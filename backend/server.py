from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os, uuid, logging, bcrypt, jwt, requests, threading
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
import base64, re
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from seed import SEED_USERS, SEED_MATERIALS, SEED_MENUS, MENU_PHOTOS

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
app = FastAPI(title="SI FOUR AM API")
api = APIRouter(prefix="/api")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("si4am")
JWT_ALG = "HS256"
NOID = {"_id": 0}
TERMS_VERSION = "2026-06-01"
PRIVACY_VERSION = "2026-06-01"
VALID_ROLES = {"owner", "admin", "barteam", "rider"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return str(uuid.uuid4())


WIB = timezone(timedelta(hours=7))


def now_wib():
    return datetime.now(WIB).strftime("%H:%M:%S")


BUNDLES = {1: {"cups": 4, "price": 45000, "name": "BUNDLING 1"}, 2: {"cups": 10, "price": 110000, "name": "BUNDLING 2"}}
ALLOWANCE = 20000
_gs_url_cache: Dict[str, Any] = {"url": None}


async def gs_url() -> Optional[str]:
    cfg = await db.config.find_one({"key": "apps_script_url"})
    return (cfg or {}).get("value") or os.environ.get("GOOGLE_APPS_SCRIPT_URL")


def _gs_post(url: str, payload: dict):
    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        logger.warning(f"Apps Script sync failed: {e}")


async def gs_sync(sheet: str, record: dict, photo: Optional[str] = None, photo_name: str = ""):
    """Fire-and-forget sync to Google Sheets / Drive via Apps Script web app."""
    url = await gs_url()
    if not url:
        return
    rec = {k: v for k, v in record.items() if k not in ("photo", "checkin_photo", "checkout_photo", "_id")}
    threading.Thread(target=_gs_post, args=(url, {"sheet": sheet, "record": rec, "photo": photo, "photo_name": photo_name}), daemon=True).start()


# ---------- Emergent Object Storage (file & media) ----------
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "sifouram"
storage_key = None


def init_storage(force: bool = False):
    global storage_key
    if storage_key and not force:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ.get("EMERGENT_LLM_KEY")}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        raise HTTPException(404, "File not found")
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


async def store_photo(data_url: Optional[str], folder: str, user_id: str) -> Optional[str]:
    """Upload a base64 data-URL image to object storage; returns /api/files/<path> URL (falls back to the data URL)."""
    if not data_url or not data_url.startswith("data:"):
        return data_url
    m = re.match(r"^data:(image/(\w+));base64,(.*)$", data_url, re.S)
    if not m:
        return data_url
    ext = "jpg" if m.group(2) == "jpeg" else m.group(2)
    path = f"{APP_NAME}/{folder}/{user_id}/{uid()}.{ext}"
    try:
        raw = base64.b64decode(m.group(3))
        res = put_object(path, raw, m.group(1))
        await db.files.insert_one({"id": uid(), "storage_path": res["path"], "folder": folder, "user_id": user_id, "content_type": m.group(1), "size": res.get("size", len(raw)), "is_deleted": False, "created_at": now_iso()})
        return f"/api/files/{res['path']}"
    except Exception as e:
        logger.warning(f"Object storage upload failed, keeping inline image: {e}")
        return data_url


def hash_pw(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def check_pw(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def make_token(user_id: str, days: int, token_type: str = "access") -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(days=days),
            "type": token_type,
        },
        os.environ["JWT_SECRET"],
        algorithm=JWT_ALG,
    )


def make_identify_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            "type": "identified",
        },
        os.environ["JWT_SECRET"],
        algorithm=JWT_ALG,
    )


def request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def public_user(u: dict) -> dict:
    return {k: v for k, v in u.items() if k not in ("_id", "password_hash", "pin_hash")}


async def get_user(request: Request) -> dict:
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    u = await db.users.find_one({"id": payload["sub"]})
    if not u or u.get("active", True) is False:
        raise HTTPException(401, "User not found")
    return u


def roles(*allowed):
    async def dep(u: dict = Depends(get_user)):
        if u["role"] not in allowed:
            raise HTTPException(403, "Forbidden for role " + u["role"])
        return u
    return dep


STAFF = roles("owner", "admin", "barteam")
SUPER = roles("owner")
REPORTS = roles("owner", "admin")
ANY = get_user


# ---------- Models ----------
class IdentifyIn(BaseModel):
    identifier: str
    terms_accepted: bool
    privacy_accepted: bool


class LoginIn(BaseModel):
    account_token: str
    pin: str
    remember: bool = False


class PinIn(BaseModel):
    pin: str


class UserCreateIn(BaseModel):
    name: str
    username: str
    role: str
    pin: str
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    password: Optional[str] = None
    active: bool = True
    photo: Optional[str] = None
    banks: Optional[list] = None


class ProfileIn(BaseModel):
    name: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    photo: Optional[str] = None
    joined_at: Optional[str] = None
    placement: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    bank_holder: Optional[str] = None
    banks: Optional[list] = None


class PasswordIn(BaseModel):
    old_password: str
    new_password: str


class PinChangeIn(BaseModel):
    password: str
    new_pin: str


class MaterialIn(BaseModel):
    name: str
    unit: str
    pack_qty: float
    pack_price: float
    pack_label: str = "pack"
    category: str = "raw"
    min_stock: float = 0


class InvTxIn(BaseModel):
    material_id: str
    type: str  # in | out | opname
    qty: float
    note: str = ""
    date: str
    item_name: str = ""
    supplier: str = ""


class RecipeItem(BaseModel):
    material_id: str
    qty: float


class MenuIn(BaseModel):
    name: str
    price: float
    max_stock: int = 30
    photo: Optional[str] = None
    recipe: List[RecipeItem] = []
    order: Optional[int] = None


class ProduceIn(BaseModel):
    menu_id: str
    qty: int
    date: str
    type: str = "produce"  # produce | adjust
    note: str = ""


class AttendanceIn(BaseModel):
    rider_id: str
    pin: str
    photo: str
    date: str
    lat: Optional[float] = None
    lng: Optional[float] = None


class RiderStockIn(BaseModel):
    rider_id: str
    date: str
    items: Dict[str, int]
    photo: Optional[str] = None


class RiderStockVerifyIn(BaseModel):
    photo: str


class SaleItem(BaseModel):
    menu_id: Optional[str] = None
    qty: int = 1
    bundle: Optional[int] = None
    components: Optional[Dict[str, int]] = None  # menu_id -> cups (for bundles)


class SalePaymentPart(BaseModel):
    method: str
    amount: float


class SaleIn(BaseModel):
    rider_id: str
    date: str
    customer_name: str = ""
    customer_phone: str = ""
    items: List[SaleItem]
    payment_method: str = "cash"
    payment_parts: List[SalePaymentPart] = []
    cash_received: float = 0
    order_type: str = "takeaway"
    table_number: str = ""
    client_id: Optional[str] = None


class DepositRow(BaseModel):
    menu_id: str
    stock: int
    remaining: int
    cash: int
    qris: int
    wastage: int


class BundleIn(BaseModel):
    bundle: int
    method: str  # cash | qris
    qty: int
    items: Dict[str, int]


class DepositIn(BaseModel):
    rider_id: str
    date: str
    pic_id: Optional[str] = None
    rows: List[DepositRow]
    bundles: List[BundleIn] = []
    debt_payment: float = 0
    expenses: float = 0
    expense_note: str = ""


class InvoiceRow(BaseModel):
    menu_id: str
    qty: int
    price: Optional[float] = None


class InvoiceIn(BaseModel):
    customer_name: str
    customer_phone: str
    date: str
    rows: List[InvoiceRow]
    payment_method: str = "cash"
    discount: float = 0
    down_payment: float = 0
    note: str = ""
    client_id: Optional[str] = None


class PayIn(BaseModel):
    amount: float
    method: str = "cash"


class ExpenseIn(BaseModel):
    date: str
    category: str
    amount: float
    note: str = ""
    account: str = "cash"
    type: str = "expense"  # expense | income


class HandoverExpense(BaseModel):
    name: str
    amount: float


class HandoverIn(BaseModel):
    date: str
    period_start: str
    period_end: str
    giver_id: str
    receiver_id: str
    expected_cash: float
    received_cash: float
    expenses: List[HandoverExpense] = []
    note: str = ""
    client_id: Optional[str] = None


class WithdrawalIn(BaseModel):
    rider_id: str
    date: str
    type: str  # allowance | incentive
    method: str  # cash | bank
    amount: float
    note: str = ""
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    bank_holder: Optional[str] = None


class ConfigIn(BaseModel):
    apps_script_url: str


class PurchaseOrderIn(BaseModel):
    material_id: str
    qty: float
    note: str = ""


class PurchaseOrderDecisionIn(BaseModel):
    note: str = ""


class BroadcastIn(BaseModel):
    roles: List[str]
    message: str


class PaymentAccountIn(BaseModel):
    name: str
    bank_name: str
    account_number: str
    account_holder: str
    active: bool = True
    qris_photo: Optional[str] = None


class GpsIn(BaseModel):
    lat: float
    lng: float


class SettingsIn(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    notifications: Optional[bool] = None
    gps_mode: Optional[str] = None
    motivation_preference: Optional[str] = None


# ---------- Seeding ----------
async def seed():
    await db.users.create_index("username", unique=True)
    await db.users.create_index("id", unique=True)
    await db.users.create_index("whatsapp")
    await db.attendance.create_index([("rider_id", 1), ("date", 1)], unique=True)
    await db.rider_stock.create_index([("rider_id", 1), ("date", 1)], unique=True)
    await db.deposits.create_index([("rider_id", 1), ("date", 1)], unique=True)
    await db.sales.create_index([("rider_id", 1), ("date", 1)])
    await db.customers.create_index("phone")
    await db.login_attempts.create_index("identifier")
    for su in SEED_USERS:
        ex = await db.users.find_one({"username": su["username"]})
        doc = {
            "name": su["name"],
            "email": su["email"].lower(),
            "whatsapp": su["whatsapp"],
            "role": su["role"],
            "active": True,
        }
        if not ex:
            doc.update({"id": uid(), "username": su["username"], "password_hash": hash_pw(su["password"]), "pin_hash": hash_pw(su["pin"]),
                        "photo": None, "joined_at": "2024-01-01", "placement": "Jakarta", "created_at": now_iso(),
                        "settings": {"theme": "dark", "language": "en", "notifications": True, "gps_mode": "while_using"}})
            await db.users.insert_one(doc)
        else:
            upd = {}
            if not check_pw(su["password"], ex["password_hash"]):
                upd["password_hash"] = hash_pw(su["password"])
            if not check_pw(su["pin"], ex.get("pin_hash", "")):
                upd["pin_hash"] = hash_pw(su["pin"])
            for key, value in doc.items():
                if ex.get(key) != value:
                    upd[key] = value
            if upd:
                await db.users.update_one({"username": su["username"]}, {"$set": upd})
    if await db.materials.count_documents({}) == 0:
        mats = []
        for name, unit, pq, pp, lbl, cat in SEED_MATERIALS:
            mats.append({"id": uid(), "name": name, "unit": unit, "pack_qty": pq, "pack_price": pp, "pack_label": lbl, "category": cat,
                         "stock": pq * 3, "min_stock": pq * 0.5, "created_at": now_iso()})
        await db.materials.insert_many(mats)
    if await db.menus.count_documents({}) == 0:
        mats = {m["name"]: m["id"] for m in await db.materials.find({}, NOID).to_list(100)}
        menus = []
        for i, (name, price, mx, recipe) in enumerate(SEED_MENUS):
            menus.append({"id": uid(), "name": name, "price": price, "max_stock": mx, "order": i + 1, "photo": MENU_PHOTOS.get(name),
                          "recipe": [{"material_id": mats[m], "qty": q} for m, q in recipe], "stock": 100, "active": True, "created_at": now_iso()})
        await db.menus.insert_many(menus)
    # migration: every menu recipe includes 1 pc of each packaging material
    pack = await db.materials.find({"category": "packaging"}, NOID).to_list(50)
    async for mn in db.menus.find({}, NOID):
        have = {r["material_id"] for r in mn.get("recipe", [])}
        add = [{"material_id": p["id"], "qty": 1} for p in pack if p["id"] not in have]
        if add:
            await db.menus.update_one({"id": mn["id"]}, {"$set": {"recipe": mn["recipe"] + add}})
    await db.sales.create_index("client_id", unique=True, sparse=True)
    await db.withdrawals.create_index([("rider_id", 1), ("date", 1)])


@app.on_event("startup")
async def on_startup():
    await seed()
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@api.get("/files/{path:path}")
async def serve_file(path: str):
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False}, NOID)
    if not rec:
        raise HTTPException(404, "File not found")
    data, ct = get_object(path)
    return Response(content=data, media_type=rec.get("content_type", ct), headers={"Cache-Control": "public, max-age=86400"})


@api.get("/files")
async def list_files(folder: Optional[str] = None, u=Depends(STAFF)):
    q = {"is_deleted": False, **({"folder": folder} if folder else {})}
    return await db.files.find(q, NOID).sort("created_at", -1).limit(200).to_list(200)


@api.delete("/files/{path:path}")
async def delete_file(path: str, u=Depends(SUPER)):
    await db.files.update_one({"storage_path": path}, {"$set": {"is_deleted": True}})
    return {"ok": True}


# ---------- Auth ----------
@api.post("/auth/identify")
async def identify_account(body: IdentifyIn):
    if not body.terms_accepted or not body.privacy_accepted:
        raise HTTPException(400, "Syarat & Ketentuan serta Kebijakan Privasi harus disetujui.")
    ident = body.identifier.strip().lower()
    phone = re.sub(r"\D", "", ident)
    u = await db.users.find_one(
        {
            "$or": [
                {"username": ident},
                {"email": ident},
                {"whatsapp": ident},
                {"whatsapp": phone},
            ]
        }
    )
    if not u or u.get("active", True) is False:
        raise HTTPException(
            404,
            "Email atau username tidak ditemukan, atau akun tidak aktif. "
            "Segera hubungi Tim Bar atau Owner.",
        )
    consent = {
        "terms_version": TERMS_VERSION,
        "privacy_version": PRIVACY_VERSION,
        "accepted_at": now_iso(),
    }
    await db.users.update_one({"id": u["id"]}, {"$set": {"consent": consent}})
    u["consent"] = consent
    return {"account_token": make_identify_token(u["id"]), "user": public_user(u)}


@api.post("/auth/login")
async def login(body: LoginIn, request: Request):
    try:
        payload = jwt.decode(body.account_token, os.environ["JWT_SECRET"], algorithms=[JWT_ALG])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Sesi identifikasi telah berakhir. Masukkan akun kembali.")
    if payload.get("type") != "identified":
        raise HTTPException(401, "Sesi identifikasi tidak valid.")
    u = await db.users.find_one({"id": payload.get("sub")})
    if not u or u.get("active", True) is False:
        raise HTTPException(
            401,
            "PIN belum didaftarkan, atau akun tidak aktif. Segera hubungi Tim Bar atau Owner.",
        )
    key = f"{request_ip(request)}:{u['id']}"
    att = await db.login_attempts.find_one({"identifier": key})
    if att and att.get("count", 0) >= 5 and datetime.fromisoformat(att["last"]) > datetime.now(timezone.utc) - timedelta(minutes=15):
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    if not u.get("pin_hash") or not check_pw(body.pin, u["pin_hash"]):
        await db.login_attempts.update_one({"identifier": key}, {"$inc": {"count": 1}, "$set": {"last": now_iso()}}, upsert=True)
        raise HTTPException(
            401,
            "PIN belum didaftarkan, atau akun tidak aktif. Segera hubungi Tim Bar atau Owner.",
        )
    await db.login_attempts.delete_one({"identifier": key})
    token = make_token(u["id"], 30 if body.remember else 1)
    return {"token": token, "user": public_user(u)}


@api.get("/auth/me")
async def me(u=Depends(ANY)):
    return public_user(u)


@api.post("/auth/verify-pin")
async def verify_pin(body: PinIn, request: Request, u=Depends(ANY)):
    if len(body.pin) != 6 or not body.pin.isdigit():
        raise HTTPException(400, "PIN harus berisi 6 angka")
    key = f"pin-gate:{request_ip(request)}:{u['id']}"
    attempt = await db.login_attempts.find_one({"identifier": key})
    if attempt and attempt.get("count", 0) >= 5:
        last_attempt = datetime.fromisoformat(attempt["last"])
        if last_attempt > datetime.now(timezone.utc) - timedelta(minutes=15):
            raise HTTPException(429, "Terlalu banyak percobaan PIN. Coba lagi dalam 15 menit.")
    if not check_pw(body.pin, u.get("pin_hash", "")):
        await db.login_attempts.update_one(
            {"identifier": key},
            {"$inc": {"count": 1}, "$set": {"last": now_iso()}},
            upsert=True,
        )
        raise HTTPException(401, "PIN salah")
    await db.login_attempts.delete_one({"identifier": key})
    return {"ok": True}


@api.put("/auth/profile")
async def update_profile(body: ProfileIn, u=Depends(ANY)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "banks" in upd and isinstance(upd["banks"], list):
        upd["banks"] = upd["banks"][:3]
    if "email" in upd:
        upd["email"] = upd["email"].lower()
    if upd.get("photo"):
        upd["photo"] = await store_photo(upd["photo"], "profiles", u["id"])
    await db.users.update_one({"id": u["id"]}, {"$set": upd})
    return public_user(await db.users.find_one({"id": u["id"]}))


@api.put("/auth/password")
async def change_password(body: PasswordIn, u=Depends(ANY)):
    if not check_pw(body.old_password, u["password_hash"]):
        raise HTTPException(400, "Old password incorrect")
    await db.users.update_one({"id": u["id"]}, {"$set": {"password_hash": hash_pw(body.new_password)}})
    return {"ok": True}


@api.put("/auth/pin")
async def change_pin(body: PinChangeIn, u=Depends(ANY)):
    if not check_pw(body.password, u["password_hash"]):
        raise HTTPException(400, "Password incorrect")
    await db.users.update_one({"id": u["id"]}, {"$set": {"pin_hash": hash_pw(body.new_pin)}})
    return {"ok": True}


@api.get("/settings")
async def get_settings(u=Depends(ANY)):
    return u.get("settings", {})


@api.put("/settings")
async def put_settings(body: SettingsIn, u=Depends(ANY)):
    upd = {f"settings.{k}": v for k, v in body.model_dump().items() if v is not None}
    await db.users.update_one({"id": u["id"]}, {"$set": upd})
    return (await db.users.find_one({"id": u["id"]}))["settings"]


@api.get("/users")
async def list_users(role: Optional[str] = None, u=Depends(ANY)):
    if u["role"] == "owner":
        q = {"role": role} if role else {}
        return await db.users.find(q, {"_id": 0, "password_hash": 0, "pin_hash": 0}).to_list(200)
    if u["role"] == "rider" and role == "owner":
        users = await db.users.find(
            {"role": "owner"},
            {"_id": 0, "id": 1, "name": 1, "whatsapp": 1, "role": 1},
        ).to_list(10)
        return users
    if u["role"] in {"admin", "barteam"} and role == "rider":
        return await db.users.find(
            {"role": "rider", "active": True},
            {"_id": 0, "id": 1, "name": 1, "role": 1, "photo": 1, "placement": 1},
        ).to_list(200)
    raise HTTPException(403, "Daftar pengguna hanya tersedia untuk Owner")


@api.post("/users")
async def create_user(body: UserCreateIn, u=Depends(SUPER)):
    username = body.username.strip().lower()
    if body.role not in VALID_ROLES:
        raise HTTPException(400, "Role tidak valid")
    if len(body.pin) != 6 or not body.pin.isdigit():
        raise HTTPException(400, "PIN harus berisi 6 angka")
    if body.photo and (not body.photo.startswith("data:image/") or len(body.photo) > 3_000_000):
        raise HTTPException(400, "Foto harus berupa gambar inline maksimal 2 MB")
    if body.banks and len(body.banks) > 3:
        raise HTTPException(400, "Maksimal tiga rekening bank")
    if await db.users.find_one({"username": username}):
        raise HTTPException(409, "Username sudah digunakan")
    doc = {
        "id": uid(),
        "name": body.name.strip(),
        "username": username,
        "email": (body.email or "").strip().lower(),
        "whatsapp": (body.whatsapp or "").strip(),
        "role": body.role,
        "active": body.active,
        "password_hash": hash_pw(body.password or uid()),
        "pin_hash": hash_pw(body.pin),
        "photo": body.photo,
        "banks": body.banks or [],
        "settings": {"theme": "dark", "language": "id", "notifications": True},
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    return public_user(doc)


# ---------- Inventory ----------
def menu_cost(menu: dict, mats: Dict[str, dict]) -> float:
    cost = 0.0
    for r in menu.get("recipe", []):
        m = mats.get(r["material_id"])
        if m and m["pack_qty"]:
            cost += r["qty"] / m["pack_qty"] * m["pack_price"]
    return round(cost)


@api.get("/materials")
async def list_materials(u=Depends(ANY)):
    return await db.materials.find({}, NOID).sort("category", 1).to_list(200)


@api.post("/materials")
async def create_material(body: MaterialIn, u=Depends(STAFF)):
    doc = {**body.model_dump(), "id": uid(), "stock": 0, "created_at": now_iso()}
    await db.materials.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/purchase-orders")
async def list_purchase_orders(u=Depends(STAFF)):
    query = {} if u["role"] in {"owner", "admin"} else {"requested_by": u["id"]}
    return await db.purchase_orders.find(query, NOID).sort("created_at", -1).to_list(300)


@api.post("/purchase-orders")
async def create_purchase_order(body: PurchaseOrderIn, u=Depends(STAFF)):
    if body.qty <= 0:
        raise HTTPException(400, "Jumlah pesanan harus lebih dari nol")
    material = await db.materials.find_one({"id": body.material_id}, NOID)
    if not material:
        raise HTTPException(404, "Bahan tidak ditemukan")
    doc = {
        "id": uid(), "material_id": material["id"], "material_name": material["name"],
        "unit": material["unit"], "qty": body.qty, "note": body.note.strip(), "status": "pending",
        "requested_by": u["id"], "requested_by_name": u["name"], "created_at": now_iso(),
        "approved_by": None, "approved_at": None, "decision_note": "",
    }
    await db.purchase_orders.insert_one(doc)
    await db.notifications.insert_one({
        "id": uid(), "for_role": "owner", "type": "purchase_order",
        "title": f"PO baru · {material['name']}",
        "body": f"{u['name']} meminta {body.qty:g} {material['unit']}",
        "ref_id": doc["id"], "read": False, "created_at": now_iso(),
    })
    await db.notifications.insert_one({
        "id": uid(), "for_role": "admin", "type": "purchase_order",
        "title": f"PO baru · {material['name']}",
        "body": f"{u['name']} meminta {body.qty:g} {material['unit']}",
        "ref_id": doc["id"], "read": False, "created_at": now_iso(),
    })
    doc.pop("_id", None)
    return doc


@api.post("/purchase-orders/{po_id}/{decision}")
async def decide_purchase_order(po_id: str, decision: str, body: PurchaseOrderDecisionIn, u=Depends(REPORTS)):
    if decision not in {"approve", "reject"}:
        raise HTTPException(400, "Keputusan PO tidak valid")
    po = await db.purchase_orders.find_one({"id": po_id}, NOID)
    if not po:
        raise HTTPException(404, "PO tidak ditemukan")
    if po["status"] != "pending":
        return po
    status = "approved" if decision == "approve" else "rejected"
    status_label = "disetujui" if status == "approved" else "ditolak"
    await db.purchase_orders.update_one({"id": po_id}, {"$set": {
        "status": status, "approved_by": u["name"], "approved_at": now_iso(),
        "decision_note": body.note.strip(),
    }})
    await db.notifications.insert_one({
        "id": uid(), "for_user": po["requested_by"], "type": "purchase_order",
        "title": f"PO {status_label} · {po['material_name']}",
        "body": body.note.strip() or f"PO {po['qty']:g} {po['unit']} telah {status_label} oleh {u['name']}",
        "ref_id": po_id, "read": False, "created_at": now_iso(),
    })
    return await db.purchase_orders.find_one({"id": po_id}, NOID)


@api.post("/broadcast")
async def broadcast_message(body: BroadcastIn, u=Depends(SUPER)):
    roles = [role for role in body.roles if role in VALID_ROLES]
    if not roles or not body.message.strip():
        raise HTTPException(400, "Pilih penerima dan tulis pesan broadcast")
    users = await db.users.find({"role": {"$in": roles}, "active": {"$ne": False}}, NOID).to_list(500)
    if users:
        await db.notifications.insert_many([{
            "id": uid(), "for_user": recipient["id"], "type": "broadcast", "title": "Info dari Owner",
            "body": body.message.strip(), "ref_id": None, "read": False, "created_at": now_iso(),
        } for recipient in users])
    return {"recipients": [{"name": recipient["name"], "whatsapp": recipient.get("whatsapp", "")} for recipient in users]}


@api.get("/payment-accounts")
async def list_payment_accounts(u=Depends(SUPER)):
    return await db.payment_accounts.find({}, NOID).sort("created_at", -1).to_list(50)


@api.get("/payment-accounts/public")
async def list_public_payment_accounts(u=Depends(ANY)):
    return await db.payment_accounts.find(
        {"active": True, "qris_photo": {"$nin": [None, ""]}},
        {"_id": 0, "id": 1, "name": 1, "bank_name": 1, "qris_photo": 1},
    ).to_list(20)


@api.post("/payment-accounts")
async def create_payment_account(body: PaymentAccountIn, u=Depends(SUPER)):
    if body.qris_photo and (not body.qris_photo.startswith("data:image/") or len(body.qris_photo) > 3_000_000):
        raise HTTPException(400, "Gambar QRIS harus berupa foto maksimal 2 MB")
    doc = {**body.model_dump(), "id": uid(), "created_by": u["id"], "created_at": now_iso()}
    if body.qris_photo:
        doc["qris_photo"] = await store_photo(body.qris_photo, "payment_accounts", u["id"])
    await db.payment_accounts.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.put("/materials/{mid}")
async def update_material(mid: str, body: MaterialIn, u=Depends(STAFF)):
    await db.materials.update_one({"id": mid}, {"$set": body.model_dump()})
    return await db.materials.find_one({"id": mid}, NOID)


@api.get("/inventory/tx")
async def list_inv_tx(start: Optional[str] = None, end: Optional[str] = None, u=Depends(ANY)):
    q = {}
    if start and end:
        q["date"] = {"$gte": start, "$lte": end}
    return await db.inventory_tx.find(q, NOID).sort("created_at", -1).to_list(500)


@api.post("/inventory/tx")
async def create_inv_tx(body: InvTxIn, u=Depends(STAFF)):
    m = await db.materials.find_one({"id": body.material_id}, NOID)
    if not m:
        raise HTTPException(404, "Material not found")
    if body.type == "in":
        new_stock = m["stock"] + body.qty
        cost = body.qty / m["pack_qty"] * m["pack_price"] if m["pack_qty"] else 0
    elif body.type == "out":
        new_stock = m["stock"] - body.qty
        cost = 0
    elif body.type == "opname":
        new_stock = body.qty
        cost = 0
    else:
        raise HTTPException(400, "Invalid type")
    await db.materials.update_one({"id": m["id"]}, {"$set": {"stock": new_stock}})
    doc = {"id": uid(), "material_id": m["id"], "material_name": m["name"], "unit": m["unit"], "type": body.type, "qty": body.qty,
           "before": m["stock"], "after": new_stock, "cost": round(cost), "note": body.note, "date": body.date, "time": now_wib(),
           "item_name": body.item_name, "supplier": body.supplier, "user": u["name"], "created_at": now_iso()}
    await db.inventory_tx.insert_one(doc)
    doc.pop("_id", None)
    await gs_sync("inventory", doc)
    return doc


# ---------- Menus & Menu stock ----------
async def menus_full():
    mats = {m["id"]: m for m in await db.materials.find({}, NOID).to_list(200)}
    menus = await db.menus.find({"active": {"$ne": False}}, NOID).sort("order", 1).to_list(100)
    for mn in menus:
        mn["cost"] = menu_cost(mn, mats)
        mn["margin"] = mn["price"] - mn["cost"]
        for r in mn["recipe"]:
            mt = mats.get(r["material_id"], {})
            r["name"] = mt.get("name")
            r["unit"] = mt.get("unit")
    return menus


@api.get("/menus")
async def list_menus(u=Depends(ANY)):
    return await menus_full()


@api.post("/menus")
async def create_menu(body: MenuIn, u=Depends(SUPER)):
    cnt = await db.menus.count_documents({})
    doc = {**body.model_dump(), "id": uid(), "stock": 0, "active": True, "created_at": now_iso()}
    doc["order"] = body.order or cnt + 1
    await db.menus.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.put("/menus/{mid}")
async def update_menu(mid: str, body: MenuIn, u=Depends(SUPER)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if upd.get("photo"):
        upd["photo"] = await store_photo(upd["photo"], "menus", u["id"])
    await db.menus.update_one({"id": mid}, {"$set": upd})
    return await db.menus.find_one({"id": mid}, NOID)


@api.delete("/menus/{mid}")
async def delete_menu(mid: str, u=Depends(SUPER)):
    await db.menus.update_one({"id": mid}, {"$set": {"active": False}})
    return {"ok": True}


@api.post("/menu-stock/produce")
async def produce(body: ProduceIn, u=Depends(STAFF)):
    mn = await db.menus.find_one({"id": body.menu_id}, NOID)
    if not mn:
        raise HTTPException(404, "Menu not found")
    if body.type == "produce":
        mats = {m["id"]: m for m in await db.materials.find({}, NOID).to_list(200)}
        for r in mn["recipe"]:
            mt = mats.get(r["material_id"])
            if mt:
                used = r["qty"] * body.qty
                await db.materials.update_one({"id": mt["id"]}, {"$inc": {"stock": -used}})
                await db.inventory_tx.insert_one({"id": uid(), "material_id": mt["id"], "material_name": mt["name"], "unit": mt["unit"], "type": "out", "qty": used,
                                                  "before": mt["stock"], "after": mt["stock"] - used, "cost": 0, "note": f"Production {mn['name']} x{body.qty}",
                                                  "date": body.date, "user": u["name"], "created_at": now_iso()})
        new_stock = mn["stock"] + body.qty
    else:
        new_stock = body.qty
    await db.menus.update_one({"id": mn["id"]}, {"$set": {"stock": new_stock}})
    doc = {"id": uid(), "menu_id": mn["id"], "menu_name": mn["name"], "type": body.type, "qty": body.qty, "before": mn["stock"], "after": new_stock,
           "note": body.note, "date": body.date, "user": u["name"], "created_at": now_iso()}
    await db.menu_stock_tx.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/menu-stock/tx")
async def menu_stock_tx(u=Depends(ANY)):
    return await db.menu_stock_tx.find({}, NOID).sort("created_at", -1).to_list(300)


# ---------- Attendance ----------
@api.get("/attendance")
async def list_attendance(start: Optional[str] = None, end: Optional[str] = None, rider_id: Optional[str] = None, u=Depends(ANY)):
    q = {}
    if start and end:
        q["date"] = {"$gte": start, "$lte": end}
    if rider_id:
        q["rider_id"] = rider_id
    return await db.attendance.find(q, NOID).sort("date", -1).to_list(500)


@api.post("/attendance/checkin")
async def checkin(body: AttendanceIn, u=Depends(ANY)):
    rider = await db.users.find_one(
        {"id": body.rider_id, "role": "rider", "active": {"$ne": False}}
    )
    if not rider or not check_pw(body.pin, rider.get("pin_hash", "")):
        raise HTTPException(401, "PIN Rider salah atau akun tidak aktif")
    if await db.attendance.find_one({"rider_id": body.rider_id, "date": body.date}):
        raise HTTPException(409, "Absen masuk hari ini sudah tercatat")
    photo_url = await store_photo(body.photo, "attendance", rider["id"])
    doc = {"id": uid(), "rider_id": rider["id"], "rider_name": rider["name"], "date": body.date, "checkin_at": now_iso(), "checkin_time": now_wib(), "checkin_photo": photo_url,
           "checkout_at": None, "checkout_time": None, "checkout_photo": None, "lat": body.lat, "lng": body.lng}
    await db.attendance.insert_one(doc)
    if body.lat is not None:
        await db.gps.update_one({"rider_id": rider["id"]}, {"$set": {"rider_id": rider["id"], "lat": body.lat, "lng": body.lng, "updated_at": now_iso()}}, upsert=True)
    doc.pop("_id", None)
    await gs_sync("attendance", {**doc, "event": "checkin"}, body.photo, f"checkin_{rider['name']}_{body.date}.jpg")
    return doc


@api.post("/attendance/checkout")
async def checkout(body: AttendanceIn, u=Depends(ANY)):
    rider = await db.users.find_one(
        {"id": body.rider_id, "role": "rider", "active": {"$ne": False}}
    )
    if not rider or not check_pw(body.pin, rider.get("pin_hash", "")):
        raise HTTPException(401, "PIN Rider salah atau akun tidak aktif")
    att = await db.attendance.find_one({"rider_id": body.rider_id, "date": body.date})
    if not att:
        raise HTTPException(404, "Absen masuk hari ini belum ditemukan")
    if att.get("checkout_at"):
        raise HTTPException(409, "Absen pulang hari ini sudah tercatat")
    await db.attendance.update_one({"id": att["id"]}, {"$set": {"checkout_at": now_iso(), "checkout_time": now_wib(), "checkout_photo": await store_photo(body.photo, "attendance", rider["id"])}})
    doc = await db.attendance.find_one({"id": att["id"]}, NOID)
    await gs_sync("attendance", {**doc, "event": "checkout"}, body.photo, f"checkout_{rider['name']}_{body.date}.jpg")
    return doc


# ---------- Rider stock ----------
@api.get("/rider-stock")
async def get_rider_stock(rider_id: str, date: str, u=Depends(ANY)):
    if u["role"] == "rider" and rider_id != u["id"]:
        raise HTTPException(403, "Rider hanya dapat melihat stock miliknya")
    return await db.rider_stock.find_one({"rider_id": rider_id, "date": date}, NOID)


@api.get("/rider-stock/history")
async def rider_stock_history(start: str, end: str, rider_id: Optional[str] = None, u=Depends(ANY)):
    if u["role"] == "rider":
        rider_id = u["id"]
    q = {"date": {"$gte": start, "$lte": end}}
    if rider_id:
        q["rider_id"] = rider_id
    return await db.rider_stock.find(q, NOID).sort("date", -1).to_list(300)


@api.post("/rider-stock")
async def save_rider_stock(body: RiderStockIn, u=Depends(STAFF)):
    rider = await db.users.find_one({"id": body.rider_id}, NOID)
    if not rider:
        raise HTTPException(404, "Rider not found")
    prev = await db.rider_stock.find_one({"rider_id": body.rider_id, "date": body.date}, NOID)
    photo = body.photo or (prev or {}).get("photo")
    if not photo:
        raise HTTPException(400, "Photo evidence is required")
    photo = await store_photo(photo, "rider_stock", rider["id"])
    prev_items = prev["items"] if prev else {}
    menus = {m["id"]: m for m in await db.menus.find({}, NOID).to_list(100)}
    for mid, qty in body.items.items():
        delta = qty - prev_items.get(mid, 0)
        if delta and mid in menus:
            await db.menus.update_one({"id": mid}, {"$inc": {"stock": -delta}})
    total = sum(body.items.values())
    doc = {"id": prev["id"] if prev else uid(), "rider_id": rider["id"], "rider_name": rider["name"], "pic_id": u["id"], "pic_name": u["name"], "date": body.date,
           "time": now_wib(), "items": body.items, "detail": {menus[k]["name"]: v for k, v in body.items.items() if k in menus}, "total": total, "photo": photo,
           "motivation": "🔥 Keep up the sales! 🚀☕", "created_by": u["name"], "updated_at": now_iso()}
    if not prev or prev.get("verified_at"):
        doc["verified_at"] = None
        doc["verified_by"] = None
        doc["verified_by_name"] = None
        doc["verification_photo"] = None
    await db.rider_stock.update_one({"rider_id": body.rider_id, "date": body.date}, {"$set": doc}, upsert=True)
    await gs_sync("rider_stock", doc, body.photo, f"stock_{rider['name']}_{body.date}.jpg")
    return doc


@api.post("/rider-stock/{stock_id}/verify")
async def verify_rider_stock(stock_id: str, body: RiderStockVerifyIn, u=Depends(ANY)):
    if u["role"] != "rider":
        raise HTTPException(403, "Pengambilan hanya dapat diverifikasi Rider")
    stock = await db.rider_stock.find_one({"id": stock_id}, NOID)
    if not stock or stock["rider_id"] != u["id"]:
        raise HTTPException(404, "Stock awal tidak ditemukan")
    if not body.photo.startswith("data:image/") or len(body.photo) > 3_000_000:
        raise HTTPException(400, "Foto verifikasi harus berupa gambar maksimal 2 MB")
    if not stock.get("verified_at"):
        verification_photo = await store_photo(body.photo, "rider_stock_verification", u["id"])
        await db.rider_stock.update_one(
            {"id": stock_id},
            {"$set": {
                "verified_at": now_iso(),
                "verified_by": u["id"],
                "verified_by_name": u["name"],
                "verification_photo": verification_photo,
            }},
        )
    return await db.rider_stock.find_one({"id": stock_id}, NOID)


# ---------- POS / Sales ----------
def sale_payment_breakdown(sale: dict) -> Dict[str, float]:
    parts = sale.get("payment_parts") or []
    if parts:
        return {
            "cash": sum(float(part.get("amount", 0)) for part in parts if part.get("method") == "cash"),
            "qris": sum(float(part.get("amount", 0)) for part in parts if part.get("method") == "qris"),
        }
    return {
        "cash": float(sale.get("total", 0)) if sale.get("payment_method") == "cash" else 0,
        "qris": float(sale.get("total", 0)) if sale.get("payment_method") == "qris" else 0,
    }


async def pos_stock(rider_id: str, date: str):
    rs = await db.rider_stock.find_one({"rider_id": rider_id, "date": date}, NOID)
    initial = rs["items"] if rs and rs.get("verified_at") else {}
    sold: Dict[str, int] = {}
    async for s in db.sales.find({"rider_id": rider_id, "date": date}, NOID):
        for it in s["items"]:
            for mid, q in (it.get("components") or {it["menu_id"]: it["qty"]}).items():
                sold[mid] = sold.get(mid, 0) + q
    menus = await menus_full()
    out = []
    for m in menus:
        out.append({"menu_id": m["id"], "name": m["name"], "price": m["price"], "photo": m.get("photo"), "order": m["order"], "cost": m["cost"],
                    "initial": initial.get(m["id"], 0), "sold": sold.get(m["id"], 0), "remaining": initial.get(m["id"], 0) - sold.get(m["id"], 0)})
    closed = await db.eod.find_one({"rider_id": rider_id, "date": date}, NOID)
    deposited = await db.deposits.find_one({"rider_id": rider_id, "date": date}, {"_id": 0, "id": 1})
    return {"has_stock": bool(rs and rs.get("verified_at")), "pending_stock": bool(rs and not rs.get("verified_at")), "closed": bool(closed), "deposited": bool(deposited), "items": out, "bundles": BUNDLES}


@api.get("/pos/stock")
async def get_pos_stock(rider_id: str, date: str, u=Depends(ANY)):
    if u["role"] == "rider" and rider_id != u["id"]:
        raise HTTPException(403, "Rider hanya dapat melihat stock POS miliknya")
    return await pos_stock(rider_id, date)


@api.get("/rider-stock/remaining")
async def rider_stock_remaining(date: str, rider_id: Optional[str] = None, u=Depends(ANY)):
    if u["role"] == "rider":
        rider_id = u["id"]
    query = {"date": date, **({"rider_id": rider_id} if rider_id else {})}
    stocks = await db.rider_stock.find(query, NOID).sort("rider_name", 1).to_list(200)
    rows = []
    for stock in stocks:
        current = await pos_stock(stock["rider_id"], date)
        rows.append({
            "stock_id": stock["id"],
            "rider_id": stock["rider_id"],
            "rider_name": stock["rider_name"],
            "verified_at": stock.get("verified_at"),
            "pending": not bool(stock.get("verified_at")),
            "verified_by_name": stock.get("verified_by_name"),
            "verification_photo": stock.get("verification_photo"),
            "items": current["items"],
            "initial_total": stock.get("total", 0),
            "remaining_total": stock.get("total", 0) if not stock.get("verified_at") else sum(item["remaining"] for item in current["items"]),
            "sold_total": sum(item["sold"] for item in current["items"]),
        })
    return rows


@api.post("/sales")
async def create_sale(body: SaleIn, u=Depends(ANY)):
    if u["role"] == "rider" and body.rider_id != u["id"]:
        raise HTTPException(403, "Riders can only sell for themselves")
    if body.client_id:
        ex = await db.sales.find_one({"client_id": body.client_id}, NOID)
        if ex:
            return ex
    st = await pos_stock(body.rider_id, body.date)
    if not st["has_stock"]:
        raise HTTPException(400, "No initial stock for today")
    if st["closed"] or st["deposited"]:
        raise HTTPException(400, "Sales are closed for today (EOD/deposit done)")
    stock = {i["menu_id"]: i for i in st["items"]}
    need: Dict[str, int] = {}
    items, total = [], 0
    for it in body.items:
        if it.bundle:
            b = BUNDLES.get(it.bundle)
            comps = it.components or {}
            if not b or sum(comps.values()) != b["cups"] * it.qty:
                raise HTTPException(400, f"Bundle {it.bundle} needs exactly {b['cups'] if b else '?'} cups per bundle")
            for mid, q in comps.items():
                if stock.get(mid, {}).get("price") != 12000:
                    raise HTTPException(400, "Only Rp 12.000 menus can be bundled")
                need[mid] = need.get(mid, 0) + q
            sub = b["price"] * it.qty
            items.append({"menu_id": None, "bundle": it.bundle, "name": f"{b['name']} ({b['cups']} cups)", "qty": it.qty, "price": b["price"], "subtotal": sub,
                          "components": comps, "component_names": {stock[m]["name"]: q for m, q in comps.items()}})
        else:
            s = stock.get(it.menu_id)
            if not s:
                raise HTTPException(404, "Menu not found")
            need[it.menu_id] = need.get(it.menu_id, 0) + it.qty
            sub = s["price"] * it.qty
            items.append({"menu_id": it.menu_id, "name": s["name"], "qty": it.qty, "price": s["price"], "subtotal": sub})
        total += sub
    for mid, q in need.items():
        if stock[mid]["remaining"] < q:
            raise HTTPException(400, f"Insufficient stock for {stock[mid]['name']} (remaining {stock[mid]['remaining']})")
    if body.order_type not in {"dine_in", "takeaway", "online"}:
        raise HTTPException(400, "Tipe pesanan tidak valid")
    if body.order_type == "dine_in" and not body.table_number.strip():
        raise HTTPException(400, "Nomor meja wajib dipilih untuk Dine In")

    allowed_payment_methods = {"cash", "qris"}
    payment_parts = [
        {"method": part.method, "amount": round(float(part.amount), 2)}
        for part in body.payment_parts
    ]
    if payment_parts:
        if any(part["method"] not in allowed_payment_methods or part["amount"] <= 0 for part in payment_parts):
            raise HTTPException(400, "Rincian pembayaran tidak valid")
        if abs(sum(part["amount"] for part in payment_parts) - total) > 0.01:
            raise HTTPException(400, "Total pembayaran harus sama dengan total pesanan")
        payment_method = "split" if len(payment_parts) > 1 else payment_parts[0]["method"]
    else:
        if body.payment_method not in allowed_payment_methods:
            raise HTTPException(400, "Metode pembayaran tidak valid")
        payment_method = body.payment_method
        payment_parts = [{"method": payment_method, "amount": total}]

    cash_part = sum(part["amount"] for part in payment_parts if part["method"] == "cash")
    if cash_part and body.cash_received < cash_part:
        raise HTTPException(400, "Nominal tunai kurang dari total pembayaran tunai")

    cnt = await db.sales.count_documents({"date": body.date})
    receipt_no = f"S4-{body.date.replace('-', '')}-{cnt + 1:04d}"
    rider = await db.users.find_one({"id": body.rider_id}, NOID)
    cash_received = body.cash_received if cash_part else total
    doc = {"id": uid(), "client_id": body.client_id or uid(), "receipt_no": receipt_no, "rider_id": body.rider_id, "rider_name": rider["name"] if rider else "", "date": body.date, "time": now_wib(),
           "customer_name": body.customer_name, "customer_phone": body.customer_phone, "items": items, "total": total, "cups": sum(need.values()),
           "payment_method": payment_method, "payment_parts": payment_parts,
           "cash_received": cash_received, "change": max(0, cash_received - cash_part),
           "order_type": body.order_type,
           "table_number": body.table_number.strip() if body.order_type == "dine_in" else "",
           "created_at": now_iso()}
    await db.sales.insert_one(doc)
    if body.customer_phone or body.customer_name:
        key = {"phone": body.customer_phone} if body.customer_phone else {"name": body.customer_name}
        points = int(total // 10000)
        await db.customers.update_one(key, {"$set": {"name": body.customer_name, "phone": body.customer_phone, "last_visit": body.date},
                                            "$inc": {"points": points, "visits": 1, "total_spent": total}, "$setOnInsert": {"id": uid(), "created_at": now_iso()}}, upsert=True)
    doc.pop("_id", None)
    await gs_sync("sales", {**doc, "items": "; ".join(f"{i['name']} x{i['qty']}" for i in items)})
    return doc


@api.get("/sales")
async def list_sales(start: str, end: str, rider_id: Optional[str] = None, u=Depends(ANY)):
    q = {"date": {"$gte": start, "$lte": end}}
    if u["role"] == "rider":
        q["rider_id"] = u["id"]
    elif rider_id:
        q["rider_id"] = rider_id
    return await db.sales.find(q, NOID).sort("created_at", -1).to_list(1000)


async def eod_summary(rider_id: str, date: str):
    st = await pos_stock(rider_id, date)
    sales = await db.sales.find({"rider_id": rider_id, "date": date}, NOID).to_list(1000)
    menus = {i["menu_id"]: {**i, "cash_qty": 0, "qris_qty": 0, "cash_amt": 0, "qris_amt": 0} for i in st["items"]}
    bundles = []
    for s in sales:
        payments = sale_payment_breakdown(s)
        cash_ratio = payments["cash"] / s["total"] if s["total"] else 0
        qris_ratio = payments["qris"] / s["total"] if s["total"] else 0
        for it in s["items"]:
            if it.get("bundle"):
                subtotal = it["subtotal"]
                bundles.append({
                    "bundle": it["bundle"],
                    "method": s["payment_method"],
                    "qty": it["qty"],
                    "items": it["components"],
                    "cash_amount": subtotal * cash_ratio,
                    "qris_amount": subtotal * qris_ratio,
                })
                for mid, q in it["components"].items():
                    if mid in menus:
                        cash_qty = min(q, max(0, round(q * cash_ratio)))
                        menus[mid]["cash_qty"] += cash_qty
                        menus[mid]["qris_qty"] += q - cash_qty
            else:
                m = menus.get(it["menu_id"])
                if m:
                    cash_qty = min(it["qty"], max(0, round(it["qty"] * cash_ratio)))
                    m["cash_qty"] += cash_qty
                    m["qris_qty"] += it["qty"] - cash_qty
                    m["cash_amt"] += it["subtotal"] * cash_ratio
                    m["qris_amt"] += it["subtotal"] * qris_ratio
    rows = list(menus.values())
    b_cash = sum(bundle["cash_amount"] for bundle in bundles)
    b_qris = sum(bundle["qris_amount"] for bundle in bundles)
    return {"rider_id": rider_id, "date": date, "rows": rows, "bundles": bundles, "transactions": len(sales), "closed": st["closed"], "deposited": st["deposited"],
            "total_cups": sum(r["sold"] for r in rows), "total_cash": sum(r["cash_amt"] for r in rows) + b_cash, "total_qris": sum(r["qris_amt"] for r in rows) + b_qris,
            "total": sum(r["cash_amt"] + r["qris_amt"] for r in rows) + b_cash + b_qris}


@api.get("/sales/eod")
async def end_of_day(rider_id: str, date: str, u=Depends(ANY)):
    return await eod_summary(rider_id, date)


class EodIn(BaseModel):
    rider_id: str
    date: str


@api.post("/sales/eod/close")
async def close_eod(body: EodIn, u=Depends(ANY)):
    if u["role"] == "rider" and body.rider_id != u["id"]:
        raise HTTPException(403, "Forbidden")
    s = await eod_summary(body.rider_id, body.date)
    doc = {"rider_id": body.rider_id, "date": body.date, "time": now_wib(), "closed_by": u["name"], "total_cups": s["total_cups"], "total_cash": s["total_cash"], "total_qris": s["total_qris"], "closed_at": now_iso()}
    await db.eod.update_one({"rider_id": body.rider_id, "date": body.date}, {"$set": doc}, upsert=True)
    await gs_sync("eod", doc)
    return {**s, "closed": True}


@api.get("/customers")
async def list_customers(u=Depends(ANY)):
    return await db.customers.find({}, NOID).sort("points", -1).to_list(500)


@api.get("/customers/lookup")
async def lookup_customer(phone: str, u=Depends(ANY)):
    p = phone.strip()
    if len(p) < 5:
        return {"customers": [], "unpaid_invoice": None}
    custs = await db.customers.find({"phone": {"$regex": f"^{p}"}}, NOID).to_list(10)
    inv = await db.invoices.find({"customer_phone": {"$regex": f"^{p}"}, "status": "unpaid"}, NOID).sort("created_at", -1).limit(1).to_list(1)
    if not custs and inv:
        custs = [{"name": inv[0]["customer_name"], "phone": inv[0]["customer_phone"]}]
    return {"customers": custs, "unpaid_invoice": inv[0] if inv else None}


# ---------- Deposits ----------
async def rider_debt(rider_id: str, before_date: str) -> float:
    last = await db.deposits.find({"rider_id": rider_id, "date": {"$lt": before_date}}, NOID).sort("date", -1).limit(1).to_list(1)
    return last[0]["remaining_debt"] if last else 0


@api.get("/deposits/debt")
async def get_debt(rider_id: str, date: str, u=Depends(ANY)):
    return {"debt": await rider_debt(rider_id, date)}


@api.get("/deposits")
async def list_deposits(start: str, end: str, rider_id: Optional[str] = None, u=Depends(ANY)):
    q = {"date": {"$gte": start, "$lte": end}}
    if u["role"] == "rider":
        q["rider_id"] = u["id"]
    elif rider_id:
        q["rider_id"] = rider_id
    return await db.deposits.find(q, NOID).sort("date", -1).to_list(500)


@api.post("/deposits")
async def save_deposit(body: DepositIn, u=Depends(STAFF)):
    rider = await db.users.find_one({"id": body.rider_id}, NOID)
    pic = await db.users.find_one({"id": body.pic_id}, NOID) if body.pic_id else u
    menus = {m["id"]: m for m in await db.menus.find({}, NOID).to_list(100)}
    # bundle cups per menu & method
    b_cups: Dict[str, Dict[str, int]] = {}
    b_cash = b_qris = 0
    bundles_out = []
    for b in body.bundles:
        spec = BUNDLES.get(b.bundle)
        if not spec or b.qty <= 0:
            continue
        if sum(b.items.values()) != spec["cups"] * b.qty:
            raise HTTPException(400, f"Bundling {b.bundle}: total cups must be {spec['cups'] * b.qty}")
        for mid, q in b.items.items():
            if menus.get(mid, {}).get("price") != 12000:
                raise HTTPException(400, "Only Rp 12.000 menus can be bundled")
            b_cups.setdefault(mid, {"cash": 0, "qris": 0})[b.method] += q
        amt = spec["price"] * b.qty
        if b.method == "cash":
            b_cash += amt
        else:
            b_qris += amt
        bundles_out.append({"bundle": b.bundle, "name": spec["name"], "method": b.method, "qty": b.qty, "amount": amt, "items": {menus[m]["name"]: q for m, q in b.items.items() if m in menus}})
    rows, cups, cash, qris, minus, wastage_total = [], 0, b_cash, b_qris, 0, 0
    for r in body.rows:
        m = menus.get(r.menu_id)
        if not m:
            continue
        bc = b_cups.get(r.menu_id, {"cash": 0, "qris": 0})
        cash_q, qris_q = r.cash + bc["cash"], r.qris + bc["qris"]
        total_sold = cash_q + qris_q
        diff = r.stock - (total_sold + r.remaining + r.wastage)
        row_minus = max(0, diff) * m["price"]
        rows.append({"menu_id": m["id"], "name": m["name"], "price": m["price"], "stock": r.stock, "remaining": r.remaining, "cash": cash_q, "qris": qris_q, "cash_manual": r.cash, "qris_manual": r.qris,
                     "bundle_cash": bc["cash"], "bundle_qris": bc["qris"], "wastage": r.wastage, "total_sold": total_sold, "diff": diff, "cash_amt": r.cash * m["price"], "qris_amt": r.qris * m["price"], "minus": row_minus})
        cups += total_sold
        cash += r.cash * m["price"]
        qris += r.qris * m["price"]
        minus += row_minus
        wastage_total += r.wastage
        if r.wastage:
            await db.menu_stock_tx.insert_one({"id": uid(), "menu_id": m["id"], "menu_name": m["name"], "type": "wastage", "qty": r.wastage, "before": m["stock"], "after": m["stock"],
                                               "note": f"Wastage rider {rider['name']}", "date": body.date, "user": u["name"], "created_at": now_iso()})
    initial_debt = await rider_debt(body.rider_id, body.date)
    remaining_debt = initial_debt + minus - body.debt_payment
    commission = ALLOWANCE if cups > 0 else 0
    net_cash = cash - body.expenses + body.debt_payment
    if cups <= 30:
        motiv = "Keep up the spirit! Let's tackle tomorrow's route with full energy! 💪🔥"
    elif cups <= 49:
        motiv = "Alhamdulillah, that's amazing! You're almost at the target, let's go all out tomorrow! 🚀📈"
    else:
        motiv = "🎉 Congratulations! Target smashed! Keep up your performance! 🏆☕"
    prev = await db.deposits.find_one({"rider_id": body.rider_id, "date": body.date}, NOID)
    cnt = await db.deposits.count_documents({})
    doc = {"id": prev["id"] if prev else uid(), "receipt_no": prev["receipt_no"] if prev else f"DEP-{body.date.replace('-', '')}-{cnt + 1:03d}",
           "rider_id": body.rider_id, "rider_name": rider["name"], "pic_id": pic["id"], "pic_name": pic["name"], "date": body.date, "time": now_wib(), "rows": rows, "bundles": bundles_out,
           "total_cups": cups, "total_cash": cash, "total_qris": qris, "total_income": cash + qris, "minus": minus, "total_wastage": wastage_total,
           "initial_debt": initial_debt, "new_debt": minus, "debt_payment": body.debt_payment, "remaining_debt": remaining_debt, "commission": commission,
           "expenses": body.expenses, "expense_note": body.expense_note, "net_cash": net_cash, "motivation": motiv, "updated_at": now_iso()}
    await db.deposits.update_one({"rider_id": body.rider_id, "date": body.date}, {"$set": doc}, upsert=True)
    await gs_sync("deposits", {**doc, "rows": "; ".join(f"{r['name']}: stock {r['stock']} sisa {r['remaining']} cash {r['cash']} qris {r['qris']} waste {r['wastage']}" for r in rows), "bundles": str(bundles_out)})
    await db.notifications.insert_one({"id": uid(), "for_role": "owner", "type": "deposit", "title": f"Setoran · {rider['name']}",
                                       "body": f"{cups} cups · Cash Rp {int(cash):,} · QRIS Rp {int(qris):,} · Net Rp {int(net_cash):,}".replace(",", "."),
                                       "ref_id": doc["id"], "read": False, "created_at": now_iso()})
    return doc


# ---------- Invoices ----------
@api.get("/invoices")
async def list_invoices(u=Depends(SUPER)):
    return await db.invoices.find({}, NOID).sort("created_at", -1).to_list(300)


@api.post("/invoices")
async def create_invoice(body: InvoiceIn, u=Depends(SUPER)):
    if body.client_id:
        ex = await db.invoices.find_one({"client_id": body.client_id}, NOID)
        if ex:
            return ex
    menus = {m["id"]: m for m in await db.menus.find({}, NOID).to_list(100)}
    rows, subtotal = [], 0
    for r in body.rows:
        m = menus.get(r.menu_id)
        if not m or r.qty <= 0:
            continue
        price = r.price if r.price is not None else m["price"]
        rows.append({"menu_id": m["id"], "name": m["name"], "qty": r.qty, "price": price, "subtotal": price * r.qty})
        subtotal += price * r.qty
    cnt = await db.invoices.count_documents({})
    total = subtotal - body.discount
    remaining = max(0, total - body.down_payment)
    doc = {"id": uid(), "client_id": body.client_id or uid(), "invoice_no": f"INV-{body.date.replace('-', '')}-{cnt + 1:03d}", "customer_name": body.customer_name, "customer_phone": body.customer_phone,
           "date": body.date, "time": now_wib(), "rows": rows, "subtotal": subtotal, "discount": body.discount, "total": total, "down_payment": body.down_payment, "paid": body.down_payment,
           "remaining": remaining, "status": "paid" if remaining <= 0 else "unpaid", "payments": ([{"date": body.date, "amount": body.down_payment, "method": body.payment_method}] if body.down_payment else []),
           "cups": sum(r["qty"] for r in rows), "payment_method": body.payment_method, "note": body.note, "created_by": u["name"], "created_at": now_iso()}
    await db.invoices.insert_one(doc)
    doc.pop("_id", None)
    await gs_sync("invoices", {**doc, "rows": "; ".join(f"{r['name']} x{r['qty']}" for r in rows), "payments": str(doc["payments"])})
    await db.notifications.insert_one({"id": uid(), "for_role": "owner", "type": "order", "title": f"Pesanan Barang · {doc['customer_name'] or '-'}",
                                       "body": f"{doc['invoice_no']} · {doc['cups']} item · Rp {int(total):,}".replace(",", "."), "ref_id": doc["id"], "read": False, "created_at": now_iso()})
    return doc


@api.post("/invoices/{iid}/pay")
async def pay_invoice(iid: str, body: PayIn, u=Depends(SUPER)):
    inv = await db.invoices.find_one({"id": iid}, NOID)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    paid = inv.get("paid", 0) + body.amount
    remaining = max(0, inv["total"] - paid)
    await db.invoices.update_one({"id": iid}, {"$set": {"paid": paid, "remaining": remaining, "status": "paid" if remaining <= 0 else "unpaid"},
                                               "$push": {"payments": {"date": datetime.now(WIB).strftime("%Y-%m-%d"), "amount": body.amount, "method": body.method}}})
    return await db.invoices.find_one({"id": iid}, NOID)


# ---------- Expenses / Handover ----------
@api.get("/expenses")
async def list_expenses(start: str, end: str, u=Depends(STAFF)):
    return await db.expenses.find({"date": {"$gte": start, "$lte": end}}, NOID).sort("date", -1).to_list(500)


@api.post("/expenses")
async def create_expense(body: ExpenseIn, u=Depends(STAFF)):
    doc = {**body.model_dump(), "id": uid(), "user": u["name"], "created_at": now_iso()}
    await db.expenses.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.delete("/expenses/{eid}")
async def delete_expense(eid: str, u=Depends(SUPER)):
    await db.expenses.delete_one({"id": eid})
    return {"ok": True}


@api.get("/handovers")
async def list_handovers(start: str, end: str, u=Depends(SUPER)):
    return await db.handovers.find({"date": {"$gte": start, "$lte": end}}, NOID).sort("created_at", -1).to_list(500)


@api.get("/handovers/expected")
async def handover_expected(start: str, end: str, u=Depends(SUPER)):
    deps = await db.deposits.find({"date": {"$gte": start, "$lte": end}}, NOID).to_list(2000)
    prev = await db.handovers.find({"period_start": start, "period_end": end}, NOID).to_list(100)
    return {"expected_cash": sum(d["net_cash"] for d in deps), "deposits": [{"date": d["date"], "rider_name": d["rider_name"], "net_cash": d["net_cash"], "pic_name": d["pic_name"]} for d in deps],
            "already_received": sum(h["received_cash"] for h in prev)}


@api.post("/handovers")
async def create_handover(body: HandoverIn, u=Depends(SUPER)):
    if body.client_id:
        ex = await db.handovers.find_one({"client_id": body.client_id}, NOID)
        if ex:
            return ex
    g = await db.users.find_one({"id": body.giver_id}, NOID)
    r = await db.users.find_one({"id": body.receiver_id}, NOID)
    total_exp = sum(e.amount for e in body.expenses)
    hid = uid()
    for e in body.expenses:
        if e.amount:
            await db.expenses.insert_one({"id": uid(), "date": body.date, "category": "Handover Expense", "amount": e.amount, "note": e.name, "account": "cash", "type": "expense",
                                          "handover_id": hid, "user": u["name"], "created_at": now_iso()})
    doc = {**body.model_dump(), "id": hid, "client_id": body.client_id or hid, "time": now_wib(), "giver_name": g["name"] if g else "", "receiver_name": r["name"] if r else "",
           "total_expenses": total_exp, "difference": body.expected_cash - body.received_cash - total_exp, "created_by": u["name"], "created_at": now_iso()}
    await db.handovers.insert_one(doc)
    doc.pop("_id", None)
    await gs_sync("handovers", {**doc, "expenses": "; ".join(f"{e.name}: {e.amount}" for e in body.expenses)})
    return doc


# ---------- Withdrawals (allowance / incentive) ----------
@api.get("/withdrawals")
async def list_withdrawals(start: str, end: str, rider_id: Optional[str] = None, u=Depends(ANY)):
    q: Dict[str, Any] = {"date": {"$gte": start, "$lte": end}}
    if u["role"] == "rider":
        q["rider_id"] = u["id"]
    elif rider_id:
        q["rider_id"] = rider_id
    return await db.withdrawals.find(q, NOID).sort("created_at", -1).to_list(500)


@api.post("/withdrawals")
async def create_withdrawal(body: WithdrawalIn, start: str, end: str, u=Depends(ANY)):
    if u["role"] == "rider" and body.rider_id != u["id"]:
        raise HTTPException(403, "Forbidden")
    sal = await salary(start, end, body.rider_id, u)
    rs = sal["riders"][0] if sal["riders"] else None
    if not rs:
        raise HTTPException(404, "Rider not found")
    avail = rs["allowance_available"] if body.type == "allowance" else rs["incentive_available"]
    if body.amount <= 0 or body.amount > avail + 0.01:
        raise HTTPException(400, f"Amount exceeds available balance ({avail:.0f})")
    doc = {**body.model_dump(), "id": uid(), "rider_name": rs["rider_name"], "time": now_wib(), "period_start": start, "period_end": end, "approved_by": u["name"],
           "bank_name": body.bank_name or u.get("bank_name"), "bank_account": body.bank_account or u.get("bank_account"), "bank_holder": body.bank_holder or u.get("bank_holder"),
           "status": "pending", "created_at": now_iso()}
    await db.withdrawals.insert_one(doc)
    doc.pop("_id", None)
    await db.notifications.insert_one({"id": uid(), "for_role": "owner", "type": "withdrawal", "title": f"{'Uang Harian' if body.type == 'allowance' else 'Insentif'} · {rs['rider_name']}",
                                       "body": f"Rp {body.amount:,.0f} via {body.method.upper()} · {body.date} {doc['time']}", "ref_id": doc["id"], "read": False, "created_at": now_iso()})
    await gs_sync("withdrawals", doc)
    return doc


@api.post("/withdrawals/{wid}/accept")
async def accept_withdrawal(wid: str, u=Depends(SUPER)):
    w = await db.withdrawals.find_one({"id": wid})
    if not w:
        raise HTTPException(404, "Withdrawal not found")
    if w.get("status") == "diterima":
        w.pop("_id", None)
        return w
    await db.withdrawals.update_one({"id": wid}, {"$set": {"status": "diterima", "accepted_by": u["name"], "accepted_at": now_iso()}})
    return await db.withdrawals.find_one({"id": wid}, NOID)


@api.get("/notifications")
async def list_notifications(u=Depends(ANY)):
    query = {"$or": [{"for_user": u["id"]}]}
    if u["role"] in {"owner", "admin"}:
        query["$or"].append({"for_role": u["role"]})
    return await db.notifications.find(query, NOID).sort("created_at", -1).limit(30).to_list(30)


@api.post("/notifications/read")
async def read_notifications(u=Depends(ANY)):
    query = {"$or": [{"for_user": u["id"]}]}
    if u["role"] in {"owner", "admin"}:
        query["$or"].append({"for_role": u["role"]})
    await db.notifications.update_many({**query, "read": False}, {"$set": {"read": True}})
    return {"ok": True}


@api.post("/notifications/clear")
async def clear_notifications(u=Depends(ANY)):
    query = {"$or": [{"for_user": u["id"]}]}
    if u["role"] in {"owner", "admin"}:
        query["$or"].append({"for_role": u["role"]})
    await db.notifications.delete_many(query)
    return {"ok": True}


class PhotoIn(BaseModel):
    photo: str


@api.put("/users/{uid}/photo")
async def update_user_photo(uid: str, body: PhotoIn, u=Depends(SUPER)):
    url = await store_photo(body.photo, "profiles", uid)
    await db.users.update_one({"id": uid}, {"$set": {"photo": url}})
    return {"photo": url}


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    banks: Optional[list] = None
    password: Optional[str] = None
    pin: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    photo: Optional[str] = None


@api.put("/users/{uid}")
async def admin_update_user(uid: str, body: UserUpdateIn, u=Depends(SUPER)):
    if uid == u["id"] and (body.active is False or (body.role and body.role != "owner")):
        raise HTTPException(400, "Owner tidak dapat menonaktifkan atau menurunkan role akunnya sendiri")
    upd = {}
    if body.photo and (not body.photo.startswith("data:image/") or len(body.photo) > 3_000_000):
        raise HTTPException(400, "Foto harus berupa gambar inline maksimal 2 MB")
    if body.banks and len(body.banks) > 3:
        raise HTTPException(400, "Maksimal tiga rekening bank")
    for k in ("name", "username", "email", "whatsapp", "banks", "role", "active", "photo"):
        v = getattr(body, k)
        if v is not None or (k == "photo" and k in body.model_fields_set):
            if k == "role" and v not in VALID_ROLES:
                raise HTTPException(400, "Role tidak valid")
            if k == "username":
                v = v.strip().lower()
                existing = await db.users.find_one({"username": v, "id": {"$ne": uid}})
                if existing:
                    raise HTTPException(409, "Username sudah digunakan")
            upd[k] = v.lower() if k == "email" else v
    if body.password:
        upd["password_hash"] = hash_pw(body.password)
    if body.pin:
        if len(body.pin) != 6 or not body.pin.isdigit():
            raise HTTPException(400, "PIN harus berisi 6 angka")
        upd["pin_hash"] = hash_pw(body.pin)
    if upd:
        await db.users.update_one({"id": uid}, {"$set": upd})
    return public_user(await db.users.find_one({"id": uid}))


class WastageIn(BaseModel):
    menu_id: str
    qty: int
    photo: str
    note: str = ""


@api.post("/inventory/wastage")
async def inventory_wastage(body: WastageIn, u=Depends(ANY)):
    if u["role"] == "rider":
        raise HTTPException(403, "Forbidden")
    if not body.photo:
        raise HTTPException(400, "Photo required")
    m = await db.menus.find_one({"id": body.menu_id})
    if not m:
        raise HTTPException(404, "Menu not found")
    url = await store_photo(body.photo, "wastage", uid())
    before = m.get("stock", 0)
    after = before - body.qty
    await db.menus.update_one({"id": body.menu_id}, {"$set": {"stock": after}})
    doc = {"id": uid(), "menu_id": m["id"], "menu_name": m["name"], "type": "wastage", "qty": body.qty, "before": before, "after": after,
           "photo_url": url, "note": body.note, "date": datetime.now(WIB).strftime("%Y-%m-%d"), "time": now_wib(), "user": u["name"], "created_at": now_iso()}
    await db.menu_stock_tx.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ---------- AI Sales Coach ----------
class CoachIn(BaseModel):
    message: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    provider: Optional[str] = "gpt"


def _overpass(lat: float, lng: float):
    q = f"""[out:json][timeout:8];(node(around:1500,{lat},{lng})[amenity~"school|university|college|hospital|marketplace|bus_station|place_of_worship|office|food_court"];node(around:1500,{lat},{lng})[shop~"mall|supermarket|department_store"];node(around:1500,{lat},{lng})[leisure~"park|sports_centre|stadium"];node(around:1500,{lat},{lng})[railway=station];node(around:1500,{lat},{lng})[public_transport=station];);out 25;"""
    hdr = {"User-Agent": "SIFOURAM/1.0"}
    for url in ("https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
        try:
            r = requests.post(url, data={"data": q}, timeout=8, headers=hdr)
            if r.status_code != 200:
                continue
            out = []
            for e in r.json().get("elements", []):
                t = e.get("tags", {})
                if t.get("name"):
                    out.append({"name": t["name"], "type": t.get("amenity") or t.get("shop") or t.get("leisure") or t.get("railway") or t.get("public_transport"), "lat": e["lat"], "lng": e["lon"]})
            return out[:15]
        except Exception:
            continue
    return []


def _area_name(lat: float, lng: float) -> str:
    try:
        r = requests.get("https://nominatim.openstreetmap.org/reverse", params={"lat": lat, "lon": lng, "format": "json", "zoom": 16}, timeout=6, headers={"User-Agent": "SIFOURAM/1.0"}).json()
        a = r.get("address", {})
        return ", ".join(x for x in [a.get("neighbourhood") or a.get("suburb"), a.get("city_district") or a.get("village"), a.get("city") or a.get("county")] if x)
    except Exception:
        return ""


@api.get("/coach/history")
async def coach_history(u=Depends(ANY)):
    return await db.coach_chats.find({"user_id": u["id"]}, NOID).sort("created_at", -1).limit(30).to_list(30)


@api.post("/coach/chat")
async def coach_chat(body: CoachIn, u=Depends(ANY)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    d = datetime.now(WIB).strftime("%Y-%m-%d")
    st = await pos_stock(u["id"], d) if u["role"] == "rider" else {"items": []}
    sold = sum(i["sold"] for i in st["items"])
    remaining = ", ".join(f"{i['name']} {i['remaining']}" for i in st["items"] if i["remaining"] > 0) or "-"
    pois = _overpass(body.lat, body.lng) if body.lat is not None else []
    area = _area_name(body.lat, body.lng) if body.lat is not None else ""
    poi_txt = "\n".join(f"- {p['name']} ({p['type']})" for p in pois) or ("(daftar POI tidak tersedia — gunakan pengetahuan umum tentang area " + (area or "sekitar rider") + ": sekolah, pasar, kantor, stasiun, masjid, taman, kos-kosan)")
    hist = await db.coach_chats.find({"user_id": u["id"]}, NOID).sort("created_at", -1).limit(6).to_list(6)
    hist_txt = "\n".join(f"Rider: {h['message']}\nCoach: {h['reply'][:300]}" for h in reversed(hist))
    system = ("Kamu adalah 'Coach SI FOUR AM', asisten AI yang hangat, cerdas, dan energik untuk tim kopi gerobak keliling (Rp5.000–12.000/cup). "
              "Jawab pertanyaan APAPUN dari pengguna dalam Bahasa Indonesia yang santai, ramah, dan membantu — entah soal jualan, motivasi, ide konten, cuaca, pengetahuan umum, atau obrolan biasa. "
              "Jawab padat (maks ±180 kata), pakai bullet & emoji secukupnya. Jika pertanyaan menyangkut jualan atau lokasi, WAJIB sertakan 2–3 lokasi ramai TERDEKAT dari daftar POI dengan alasan & jam terbaik, plus 1 taktik jualan konkret (sapaan, bundling 4 cup Rp45.000 / 10 cup Rp110.000, upsell). "
              "Untuk pertanyaan lain, jawab langsung & akurat, lalu bila relevan kaitkan dengan cara menambah penjualan kopi. Selalu tutup dengan 1 kalimat penyemangat. "
              f"\nKONTEKS: waktu {datetime.now(WIB).strftime('%A %H:%M')} WIB. Lokasi rider: {area or 'tidak diketahui'}. User: {u['name']} ({u['role']}). Terjual hari ini {sold} cup (target 50). Sisa stok: {remaining}.\nPOI radius 1,5 km:\n{poi_txt}\n\nRiwayat:\n{hist_txt}")
    models = {"gpt": ("openai", "gpt-5.4"), "claude": ("anthropic", "claude-sonnet-4-6"), "gemini": ("gemini", "gemini-3.1-pro-preview")}
    prov, model = models.get(body.provider or "gpt", ("openai", "gpt-5.4"))
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"coach-{u['id']}", system_message=system).with_model(prov, model)
    reply = await chat.send_message(UserMessage(text=body.message))
    doc = {"id": uid(), "user_id": u["id"], "message": body.message, "reply": reply, "provider": body.provider or "gpt", "pois": pois, "area": area, "sold": sold, "created_at": now_iso()}
    await db.coach_chats.insert_one(doc)
    doc.pop("_id", None)
    return doc


class PromoIn(BaseModel):
    theme: Optional[str] = None


@api.post("/promo/idea")
async def promo_idea(body: PromoIn, u=Depends(SUPER)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    system = ("Kamu copywriter promosi WhatsApp untuk 'SI FOUR AM', kopi gerobak keliling (Rp5.000–12.000/cup, ada bundling 4 cup Rp45.000 & 10 cup Rp110.000). "
              "Buat 1 pesan promo WhatsApp Bahasa Indonesia yang singkat (maks 60 kata), hangat, persuasif, pakai emoji secukupnya, sebut nama toko SI FOUR AM, ada ajakan beli & sebut bundling. "
              "Boleh pakai token {nama} sebagai sapaan nama pelanggan. Jangan pakai placeholder kurung siku lain. Balas HANYA teks pesannya saja.")
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"promo-{u['id']}", system_message=system).with_model("openai", "gpt-5.4-mini")
    text = await chat.send_message(UserMessage(text=(body.theme or "promo menarik hari ini untuk menarik pelanggan")))
    return {"text": text}


# ---------- Aggregations ----------
async def daily_summaries(start: str, end: str, rider_id: Optional[str] = None):
    """One record per (rider, date): deposit wins over POS sales."""
    q: Dict[str, Any] = {"date": {"$gte": start, "$lte": end}}
    if rider_id:
        q["rider_id"] = rider_id
    recs: Dict[str, dict] = {}
    async for d in db.deposits.find(q, NOID):
        recs[f"{d['rider_id']}|{d['date']}"] = {"rider_id": d["rider_id"], "rider_name": d["rider_name"], "date": d["date"], "cups": d["total_cups"],
                                                 "cash": d["total_cash"], "qris": d["total_qris"], "source": "deposit",
                                                 "menu": {r["name"]: r["total_sold"] for r in d["rows"]}}
    async for s in db.sales.find(q, NOID):
        k = f"{s['rider_id']}|{s['date']}"
        if k in recs and recs[k]["source"] == "deposit":
            continue
        r = recs.setdefault(k, {"rider_id": s["rider_id"], "rider_name": s["rider_name"], "date": s["date"], "cups": 0, "cash": 0, "qris": 0, "source": "pos", "menu": {}})
        r["cups"] += s["cups"]
        payments = sale_payment_breakdown(s)
        r["cash"] += payments["cash"]
        r["qris"] += payments["qris"]
        for it in s["items"]:
            r["menu"][it["name"]] = r["menu"].get(it["name"], 0) + it["qty"]
    return list(recs.values())


RIDER_RANKS = [
    ("Herald", 0, 1750000, 20000, 0.00),
    ("Warriors", 1750000, 2520000, 30000, 0.05),
    ("Masters", 2520000, 3220000, 35000, 0.07),
    ("Divine", 3220000, 4000000, 40000, 0.10),
    ("Immortal", 4000000, None, 50000, 0.15),
]


def rider_rank_for(gross: float) -> dict:
    for index, (name, minimum, maximum, attendance, commission) in enumerate(RIDER_RANKS):
        if maximum is None or gross < maximum:
            next_rank = RIDER_RANKS[index + 1] if index + 1 < len(RIDER_RANKS) else None
            return {
                "name": name,
                "minimum": minimum,
                "maximum": maximum,
                "attendance_benefit": attendance,
                "commission_pct": commission,
                "next": {
                    "name": next_rank[0],
                    "minimum": next_rank[1],
                } if next_rank else None,
            }
    return {}


def tier_for(gross: float, days: int):
    del days
    rank = rider_rank_for(gross)
    return rank.get("name", "Herald"), rank.get("commission_pct", 0.0)


@api.get("/rider-rank")
async def rider_rank(start: str, end: str, rider_id: Optional[str] = None, u=Depends(ANY)):
    target_id = u["id"] if u["role"] == "rider" else rider_id
    if not target_id:
        raise HTTPException(400, "Pilih rider")
    recs = await daily_summaries(start, end, target_id)
    gross = sum(item["cash"] + item["qris"] for item in recs)
    attendance_days = await db.attendance.count_documents(
        {"rider_id": target_id, "date": {"$gte": start, "$lte": end}}
    )
    rank = rider_rank_for(gross)
    next_minimum = rank.get("next", {}).get("minimum") if rank.get("next") else None
    return {
        "rider_id": target_id,
        "start": start,
        "end": end,
        "gross": gross,
        "attendance_days": attendance_days,
        "rank": rank,
        "attendance_total": rank.get("attendance_benefit", 0) * attendance_days,
        "commission": round(gross * rank.get("commission_pct", 0)),
        "main_estimated_commission": round(gross * rank.get("commission_pct", 0)),
        "progress": 100 if not next_minimum else round(min(100, gross / next_minimum * 100), 1),
        "remaining": 0 if not next_minimum else max(0, next_minimum - gross),
    }


@api.get("/reports/sales")
async def sales_report(
    start: str,
    end: str,
    payment_method: Optional[str] = None,
    order_type: Optional[str] = None,
    sale_kind: Optional[str] = None,
    service_type: Optional[str] = None,
    u=Depends(REPORTS),
):
    query: Dict[str, Any] = {"date": {"$gte": start, "$lte": end}}
    rows = await db.sales.find(query, NOID).sort([("date", 1), ("time", 1)]).to_list(5000)
    filtered = []
    for sale in rows:
        current_sale_kind = "bundling" if any(item.get("bundle") for item in sale["items"]) else "regular"
        requested_sale_kind = sale_kind or order_type
        if requested_sale_kind and requested_sale_kind != "all" and current_sale_kind != requested_sale_kind:
            continue
        current_service_type = sale.get("order_type") or "takeaway"
        if service_type and service_type != "all" and current_service_type != service_type:
            continue
        payments = sale_payment_breakdown(sale)
        if payment_method and payment_method != "all" and not payments.get(payment_method, 0):
            continue
        sale["sale_kind"] = current_sale_kind
        sale["service_type"] = current_service_type
        sale["report_amount"] = payments.get(payment_method, 0) if payment_method and payment_method != "all" else sale["total"]
        sale["payment_breakdown"] = payments
        filtered.append(sale)
    by_date: Dict[str, float] = {}
    by_payment: Dict[str, float] = {}
    by_type: Dict[str, float] = {}
    by_service: Dict[str, float] = {}
    by_hour: Dict[str, dict] = {}
    products: Dict[str, dict] = {}
    for sale in filtered:
        amount = sale["report_amount"]
        allocation = amount / sale["total"] if sale["total"] else 0
        by_date[sale["date"]] = by_date.get(sale["date"], 0) + amount
        for method, value in sale["payment_breakdown"].items():
            if value:
                by_payment[method] = by_payment.get(method, 0) + value
        kind = sale["sale_kind"]
        by_type[kind] = by_type.get(kind, 0) + amount
        service = sale["service_type"]
        by_service[service] = by_service.get(service, 0) + amount
        hour = (sale.get("time") or "00:00")[:2]
        hour_row = by_hour.setdefault(hour, {"hour": f"{hour}:00", "transactions": 0, "revenue": 0})
        hour_row["transactions"] += 1
        hour_row["revenue"] += amount
        for item in sale["items"]:
            if item.get("bundle"):
                names = item.get("component_names", {})
                cup_total = sum(names.values()) or 1
                for name, quantity in names.items():
                    item_row = products.setdefault(name, {"name": name, "qty": 0, "revenue": 0})
                    item_row["qty"] += quantity
                    item_row["revenue"] += item["subtotal"] * quantity / cup_total * allocation
            else:
                item_row = products.setdefault(item["name"], {"name": item["name"], "qty": 0, "revenue": 0})
                item_row["qty"] += item["qty"]
                item_row["revenue"] += item["subtotal"] * allocation
    total_revenue = sum(sale["report_amount"] for sale in filtered)
    for item in products.values():
        item["revenue"] = round(item["revenue"])
    product_rows = sorted(products.values(), key=lambda item: (-item["revenue"], -item["qty"]))
    for index, item in enumerate(product_rows, start=1):
        item["rank"] = index
    return {
        "filters": {
            "start": start,
            "end": end,
            "payment_method": payment_method,
            "sale_kind": sale_kind or order_type,
            "service_type": service_type,
        },
        "transactions": len(filtered),
        "revenue": total_revenue,
        "average_order": round(total_revenue / len(filtered)) if filtered else 0,
        "discount": 0,
        "daily_revenue": [{"date": key, "revenue": value} for key, value in sorted(by_date.items())],
        "payment_distribution": [{"name": key.upper(), "value": value} for key, value in by_payment.items()],
        "order_distribution": [{"name": key, "value": value} for key, value in by_type.items()],
        "service_distribution": [{"name": key, "value": value} for key, value in by_service.items()],
        "hourly": [by_hour[key] for key in sorted(by_hour)],
        "products": product_rows,
    }


@api.get("/reports/operations")
async def operations_report(kind: str, start: str, end: str, u=Depends(REPORTS)):
    date_query = {"date": {"$gte": start, "$lte": end}}
    if kind == "wastage":
        rows = await db.menu_stock_tx.find({**date_query, "type": "wastage"}, NOID).to_list(2000)
        menus = {menu["id"]: menu for menu in await db.menus.find({}, NOID).to_list(500)}
        output = []
        reasons: Dict[str, float] = {}
        for row in rows:
            menu = menus.get(row.get("menu_id"), {})
            value = round(row.get("qty", 0) * menu.get("cost", menu.get("price", 0)))
            reason = row.get("note") or "Tanpa alasan"
            reasons[reason] = reasons.get(reason, 0) + value
            output.append({**row, "value": value, "reason": reason})
        output.sort(key=lambda row: -row["value"])
        largest_reason = max(reasons, key=reasons.get) if reasons else "—"
        return {
            "kind": kind,
            "rows": output,
            "summary": {
                "total_value": sum(row["value"] for row in output),
                "count": len(output),
                "largest_reason": largest_reason,
                "largest_reason_value": reasons.get(largest_reason, 0),
            },
        }
    if kind == "purchases":
        rows = await db.inventory_tx.find({**date_query, "type": "in"}, NOID).to_list(2000)
        rows.sort(key=lambda row: (row.get("date", ""), row.get("time", "")), reverse=True)
        suppliers = {row.get("supplier") or "Tanpa supplier" for row in rows}
        return {
            "kind": kind,
            "rows": rows,
            "summary": {
                "total_cost": sum(row.get("cost", 0) for row in rows),
                "count": len(rows),
                "supplier_count": len(suppliers) if rows else 0,
            },
        }
    if kind == "opname":
        rows = await db.inventory_tx.find({**date_query, "type": "opname"}, NOID).to_list(2000)
        materials = {item["id"]: item for item in await db.materials.find({}, NOID).to_list(500)}
        output = []
        for row in rows:
            material = materials.get(row["material_id"], {})
            unit_cost = material.get("pack_price", 0) / material.get("pack_qty", 1)
            difference = row.get("after", 0) - row.get("before", 0)
            output.append({**row, "difference": difference, "difference_value": round(difference * unit_cost)})
        positive = sum(row["difference_value"] for row in output if row["difference_value"] > 0)
        negative = abs(sum(row["difference_value"] for row in output if row["difference_value"] < 0))
        return {
            "kind": kind,
            "rows": output,
            "summary": {
                "count": len(output),
                "positive_value": positive,
                "negative_value": negative,
                "accuracy": max(0, round(100 - (sum(abs(row["difference"]) for row in output) / sum(max(row.get("before", 0), 1) for row in output) * 100), 1)) if output else None,
            },
        }
    if kind == "inventory":
        materials = await db.materials.find({}, NOID).to_list(500)
        menus = await menus_full()
        material_rows = [{
            "name": material["name"],
            "category": material.get("category", "raw"),
            "type": "Bahan baku",
            "qty": material.get("stock", 0),
            "unit": material.get("unit", ""),
            "unit_cost": round(material.get("pack_price", 0) / material.get("pack_qty", 1)),
            "value": round(material.get("stock", 0) / material.get("pack_qty", 1) * material.get("pack_price", 0)),
        } for material in materials]
        menu_rows = [{
            "name": menu["name"],
            "category": "Produk",
            "type": "Produk",
            "qty": menu.get("stock", 0),
            "unit": "cup",
            "unit_cost": menu.get("cost", 0),
            "value": round(menu.get("stock", 0) * menu.get("cost", 0)),
        } for menu in menus]
        rows = sorted(material_rows + menu_rows, key=lambda row: -row["value"])
        return {
            "kind": kind,
            "rows": rows,
            "summary": {
                "total_value": sum(row["value"] for row in rows),
                "product_value": sum(row["value"] for row in menu_rows),
                "material_value": sum(row["value"] for row in material_rows),
                "item_count": len(rows),
            },
        }
    raise HTTPException(400, "Jenis laporan tidak valid")


@api.get("/dashboard/summary")
async def dashboard_summary(start: str, end: str, rider_id: Optional[str] = None, u=Depends(ANY)):
    if u["role"] == "rider":
        rider_id = u["id"]
    recs = await daily_summaries(start, end, rider_id)
    by_rider: Dict[str, dict] = {}
    by_date: Dict[str, dict] = {}
    by_menu: Dict[str, int] = {}
    for r in recs:
        br = by_rider.setdefault(r["rider_id"], {"rider_id": r["rider_id"], "rider_name": r["rider_name"], "cups": 0, "cash": 0, "qris": 0, "days": 0})
        br["cups"] += r["cups"]; br["cash"] += r["cash"]; br["qris"] += r["qris"]; br["days"] += 1
        bd = by_date.setdefault(r["date"], {"date": r["date"], "cups": 0, "cash": 0, "qris": 0})
        bd["cups"] += r["cups"]; bd["cash"] += r["cash"]; bd["qris"] += r["qris"]
        for k, v in r["menu"].items():
            by_menu[k] = by_menu.get(k, 0) + v
    exp_q = {"date": {"$gte": start, "$lte": end}}
    expenses = await db.expenses.find(exp_q, NOID).to_list(1000) if u["role"] != "rider" else []
    purchases = await db.inventory_tx.find({**exp_q, "type": "in"}, NOID).to_list(1000) if u["role"] != "rider" else []
    invoices = await db.invoices.find(exp_q, NOID).to_list(1000) if u["role"] == "owner" else []
    total_exp = sum(e["amount"] for e in expenses if e.get("type", "expense") == "expense") + sum(p["cost"] for p in purchases)
    inv_income = sum(i["total"] for i in invoices)
    for bd in by_date.values():
        bd["expenses"] = sum(e["amount"] for e in expenses if e["date"] == bd["date"] and e.get("type", "expense") == "expense") + sum(p["cost"] for p in purchases if p["date"] == bd["date"])
    return {"cups": sum(r["cups"] for r in recs), "cash": sum(r["cash"] for r in recs), "qris": sum(r["qris"] for r in recs), "invoice_income": inv_income,
            "expenses": total_exp, "transactions": await db.sales.count_documents({**exp_q, **({"rider_id": rider_id} if rider_id else {})}),
            "by_rider": sorted(by_rider.values(), key=lambda x: -(x["cash"] + x["qris"])), "by_date": sorted(by_date.values(), key=lambda x: x["date"]),
            "by_menu": sorted([{"name": k, "qty": v} for k, v in by_menu.items()], key=lambda x: -x["qty"]), "days": len(set(r["date"] for r in recs))}


@api.get("/salary")
async def salary(start: str, end: str, rider_id: Optional[str] = None, u=Depends(ANY)):
    if u["role"] == "rider":
        rider_id = u["id"]
    riders = await db.users.find({"role": "rider", **({"id": rider_id} if rider_id else {})}, {"_id": 0, "password_hash": 0, "pin_hash": 0}).to_list(50)
    recs = await daily_summaries(start, end, rider_id)
    att_q = {"date": {"$gte": start, "$lte": end}}
    if rider_id:
        att_q["rider_id"] = rider_id
    atts = await db.attendance.find(att_q, NOID).to_list(2000)
    wds = await db.withdrawals.find(att_q, NOID).to_list(2000)
    out = []
    for r in riders:
        mine = [x for x in recs if x["rider_id"] == r["id"]]
        gross = sum(x["cash"] + x["qris"] for x in mine)
        cups = sum(x["cups"] for x in mine)
        att_days = len([a for a in atts if a["rider_id"] == r["id"]])
        sale_days = set(x["date"] for x in mine)
        allowance_days = len(set([a["date"] for a in atts if a["rider_id"] == r["id"]] + list(sale_days)))
        allowance = allowance_days * ALLOWANCE
        rank = rider_rank_for(gross)
        tier, pct = tier_for(gross, att_days)
        incentive = round(gross * pct)
        aw = sum(w["amount"] for w in wds if w["rider_id"] == r["id"] and w["type"] == "allowance")
        iw = sum(w["amount"] for w in wds if w["rider_id"] == r["id"] and w["type"] == "incentive")
        next_rank = rank.get("next")
        next_details = next(
            (
                (name, minimum, commission)
                for name, minimum, _maximum, _attendance, commission in RIDER_RANKS
                if next_rank and name == next_rank["name"]
            ),
            None,
        )
        out.append({"rider_id": r["id"], "rider_name": r["name"], "photo": r.get("photo"), "joined_at": r.get("joined_at"), "placement": r.get("placement"),
                    "banks": r.get("banks") or ([{"bank_name": r.get("bank_name"), "bank_account": r.get("bank_account"), "bank_holder": r.get("bank_holder")}] if r.get("bank_name") else []),
                    "gross": gross, "cups": cups, "attendance_days": att_days, "sales_days": len(sale_days), "allowance_days": allowance_days,
                    "allowance": allowance, "allowance_withdrawn": aw, "allowance_available": allowance - aw, "tier": tier, "incentive_pct": pct, "incentive": incentive,
                    "incentive_withdrawn": iw, "incentive_available": incentive - iw, "total_income": allowance + incentive,
                    "next_tier": {
                        "name": next_details[0],
                        "threshold": next_details[1],
                        "pct": next_details[2],
                        "min_days": 0,
                        "remaining": max(0, next_details[1] - gross),
                        "progress": round(min(100, gross / next_details[1] * 100), 1),
                    } if next_details else None})
    return {
        "riders": out,
        "tiers": [
            {"name": name, "threshold": minimum, "pct": commission, "min_days": 0}
            for name, minimum, _maximum, _attendance, commission in RIDER_RANKS
        ],
        "rider_count": len(out),
    }


@api.get("/finance/summary")
async def finance_summary(start: str, end: str, u=Depends(SUPER)):
    recs = await daily_summaries(start, end)
    expenses = await db.expenses.find({"date": {"$gte": start, "$lte": end}}, NOID).to_list(2000)
    purchases = await db.inventory_tx.find({"date": {"$gte": start, "$lte": end}, "type": "in"}, NOID).to_list(2000)
    invoices = await db.invoices.find({"date": {"$gte": start, "$lte": end}}, NOID).to_list(1000)
    handovers = await db.handovers.find({"date": {"$gte": start, "$lte": end}}, NOID).to_list(1000)
    ledger = []
    for r in recs:
        if r["cash"]:
            ledger.append({"date": r["date"], "type": "in", "account": "cash", "category": "Rider Sales (Cash)", "desc": r["rider_name"], "amount": r["cash"]})
        if r["qris"]:
            ledger.append({"date": r["date"], "type": "in", "account": "bank", "category": "Rider Sales (QRIS)", "desc": r["rider_name"], "amount": r["qris"]})
    for i in invoices:
        ledger.append({"date": i["date"], "type": "in", "account": "cash" if i["payment_method"] == "cash" else "bank", "category": "Order Invoice", "desc": f"{i['invoice_no']} {i['customer_name']}", "amount": i["total"]})
    for p in purchases:
        if p["cost"]:
            ledger.append({"date": p["date"], "type": "out", "account": "cash", "category": "Purchase", "desc": f"{p.get('item_name') or p['material_name']} → {p['material_name']} +{p['qty']}{p['unit']}" + (f" ({p['supplier']})" if p.get("supplier") else ""), "amount": p["cost"], "item_name": p.get("item_name", ""), "material_name": p["material_name"]})
    for e in expenses:
        ledger.append({"date": e["date"], "type": "in" if e.get("type") == "income" else "out", "account": e.get("account", "cash"), "category": e["category"], "desc": e.get("note", ""), "amount": e["amount"], "id": e["id"]})
    for w in await db.withdrawals.find({"date": {"$gte": start, "$lte": end}}, NOID).to_list(2000):
        ledger.append({"date": w["date"], "type": "out", "account": w["method"], "category": "Rider Allowance" if w["type"] == "allowance" else "Rider Incentive", "desc": w["rider_name"], "amount": w["amount"]})
    ledger.sort(key=lambda x: x["date"])
    bal = {"cash": 0, "bank": 0}
    for l in ledger:
        bal[l["account"]] += l["amount"] if l["type"] == "in" else -l["amount"]
        l["balance_cash"], l["balance_bank"] = bal["cash"], bal["bank"]
    income = sum(l["amount"] for l in ledger if l["type"] == "in")
    outgo = sum(l["amount"] for l in ledger if l["type"] == "out")
    cat: Dict[str, float] = {}
    for l in ledger:
        if l["type"] == "out":
            cat[l["category"]] = cat.get(l["category"], 0) + l["amount"]
    mats = {m["id"]: m for m in await db.materials.find({}, NOID).to_list(200)}
    menus = await db.menus.find({}, NOID).to_list(100)
    cogs = 0
    menu_cost_map = {m["name"]: menu_cost(m, mats) for m in menus}
    for r in recs:
        for name, qty in r["menu"].items():
            cogs += menu_cost_map.get(name, 0) * qty
    return {"income": income, "outgo": outgo, "net": income - outgo, "cash_balance": bal["cash"], "bank_balance": bal["bank"], "cogs": cogs,
            "gross_profit": income - cogs, "handover_total": sum(h.get("received_cash", h.get("amount", 0)) for h in handovers), "ledger": list(reversed(ledger)),
            "by_category": [{"name": k, "amount": v} for k, v in cat.items()], "inventory_value": sum(m["stock"] / m["pack_qty"] * m["pack_price"] for m in mats.values() if m["pack_qty"])}


# ---------- GPS ----------
@api.post("/gps")
async def post_gps(body: GpsIn, u=Depends(ANY)):
    if u["role"] != "rider":
        raise HTTPException(403, "GPS hanya untuk rider")
    date = datetime.now(WIB).strftime("%Y-%m-%d")
    attendance = await db.attendance.find_one({"rider_id": u["id"], "date": date, "checkout_at": None})
    if not attendance:
        raise HTTPException(403, "GPS hanya dikirim saat rider sedang bertugas")
    await db.gps.update_one({"rider_id": u["id"]}, {"$set": {"rider_id": u["id"], "rider_name": u["name"], "lat": body.lat, "lng": body.lng, "updated_at": now_iso()}}, upsert=True)
    return {"ok": True}


@api.get("/attendance/on-duty")
async def attendance_on_duty(u=Depends(ANY)):
    if u["role"] != "rider":
        return {"on_duty": False}
    date = datetime.now(WIB).strftime("%Y-%m-%d")
    record = await db.attendance.find_one({"rider_id": u["id"], "date": date, "checkout_at": None})
    return {"on_duty": bool(record), "date": date}


@api.get("/gps/active")
async def gps_active(date: str, u=Depends(SUPER)):
    atts = await db.attendance.find({"date": date, "checkout_at": None}, NOID).to_list(100)
    ids = [a["rider_id"] for a in atts]
    pts = await db.gps.find({"rider_id": {"$in": ids}}, NOID).to_list(100)
    names = {a["rider_id"]: a["rider_name"] for a in atts}
    for p in pts:
        p["rider_name"] = names.get(p["rider_id"], p.get("rider_name"))
    return pts


@api.get("/config")
async def get_config(u=Depends(STAFF)):
    return {"apps_script_url": await gs_url() or ""}


@api.put("/config")
async def put_config(body: ConfigIn, u=Depends(SUPER)):
    await db.config.update_one({"key": "apps_script_url"}, {"$set": {"key": "apps_script_url", "value": body.apps_script_url.strip()}}, upsert=True)
    return {"apps_script_url": body.apps_script_url.strip()}


HOLIDAYS_ID = {"2026-01-01", "2026-01-16", "2026-02-17", "2026-03-19", "2026-03-20", "2026-03-21", "2026-04-03", "2026-05-01", "2026-05-14", "2026-05-27", "2026-05-31", "2026-06-01", "2026-06-16", "2026-08-17", "2026-12-25"}


@api.get("/forecast")
async def forecast(rider_id: str, date: str, u=Depends(ANY)):
    """Suggest tomorrow's initial stock per menu from sales history (same weekday + recent trend + holiday uplift)."""
    target = datetime.strptime(date, "%Y-%m-%d")
    start = (target - timedelta(days=56)).strftime("%Y-%m-%d")
    recs = await daily_summaries(start, (target - timedelta(days=1)).strftime("%Y-%m-%d"), rider_id)
    menus = await db.menus.find({"active": {"$ne": False}}, NOID).sort("order", 1).to_list(100)
    same_wd = [r for r in recs if datetime.strptime(r["date"], "%Y-%m-%d").weekday() == target.weekday()]
    recent = [r for r in recs if r["date"] >= (target - timedelta(days=14)).strftime("%Y-%m-%d")]
    factor = 1.2 if (date in HOLIDAYS_ID or target.weekday() >= 5) else 1.0
    out, basis = [], "history"
    for m in menus:
        a = [r["menu"].get(m["name"], 0) for r in same_wd]
        b = [r["menu"].get(m["name"], 0) for r in recent]
        avg_a = sum(a) / len(a) if a else 0
        avg_b = sum(b) / len(b) if b else 0
        base = 0.6 * avg_a + 0.4 * avg_b if (a or b) else 0
        if not (a or b):
            basis = "default"
            base = 10 if m["price"] == 12000 else 8
        sug = min(m["max_stock"], max(3, int(round(base * factor * 1.1 + 0.5))))
        out.append({"menu_id": m["id"], "name": m["name"], "suggested": sug, "avg_same_weekday": round(avg_a, 1), "avg_recent": round(avg_b, 1)})
    return {"date": date, "rider_id": rider_id, "factor": factor, "holiday": date in HOLIDAYS_ID, "weekend": target.weekday() >= 5, "basis": basis, "days_of_history": len(recs), "items": out, "total": sum(i["suggested"] for i in out)}


@api.get("/")
async def root():
    return {"app": "SI FOUR AM", "status": "ok"}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','), allow_methods=["*"], allow_headers=["*"])


@app.on_event("shutdown")
async def shutdown():
    client.close()
