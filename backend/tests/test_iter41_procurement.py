# Iter41: Procurement P0 - multi-material PO, Admin review -> Owner approve -> ship -> Barang Datang, proof security, share intent
import os
import io
import uuid
import random
import base64
import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from PIL import Image, ImageDraw

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
PIN = "246813"
TAG = "TEST_IT41_" + uuid.uuid4().hex[:6]


def receipt_image(fmt="PNG"):
    img = Image.new("RGB", (240, 320), "white")
    d = ImageDraw.Draw(img)
    d.text((10, 10), "NOTA BARANG DATANG", fill="black")
    for i in range(14):
        d.text((10, 30 + i * 18), f"Item {i} .... Rp {random.randint(1000, 99999)}", fill="black")
        d.line((10, 44 + i * 18, 230, 44 + i * 18), fill=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, fmt)
    mime = {"PNG": "png", "JPEG": "jpeg", "WEBP": "webp"}[fmt]
    return f"data:image/{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def blank_image():
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def login(i, p):
    s = requests.Session()
    r = s.post(f"{API}/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": p, "remember": True})
    assert r.status_code == 200, r.text
    assert "si4am_session" in s.cookies
    return s


@pytest.fixture(scope="module")
def ctx():
    files_before = {f["id"] for f in mdb.files.find({}, {"_id": 0, "id": 1})}
    owner = login("baa", "130994")
    c = {"owner": owner, "users": {}, "pos": []}
    for role in ["admin", "barteam", "rider", "barteam2"]:
        un = f"qa41_{role}_{uuid.uuid4().hex[:4]}"
        real_role = "barteam" if role == "barteam2" else role
        r = owner.post(f"{API}/users", json={"name": f"{TAG} {role}", "username": un, "role": real_role, "pin": PIN})
        assert r.status_code == 200, r.text
        c["users"][role] = r.json()
        c[role] = login(un, PIN)
    mats = []
    for i in range(2):
        m = {"id": f"qa41mat_{uuid.uuid4().hex[:8]}", "name": f"{TAG} Bahan {i}", "unit": "gr", "pack_qty": 1000,
             "pack_price": 50000, "pack_label": "pack", "category": "raw", "min_stock": 500, "stock": 100 + i,
             "created_at": "2026-01-01T00:00:00Z"}
        mdb.materials.insert_one(dict(m))
        mats.append(m)
    c["mats"] = mats
    yield c
    ids = [u["id"] for u in c["users"].values()]
    po_ids = c["pos"] + [p["id"] for p in mdb.purchase_orders.find({"requested_by": {"$in": ids}}, {"id": 1})]
    mdb.purchase_orders.delete_many({"id": {"$in": po_ids}})
    mdb.notifications.delete_many({"$or": [{"for_user": {"$in": ids}}, {"ref_id": {"$in": po_ids}}]})
    mdb.inventory_tx.delete_many({"$or": [{"purchase_order_id": {"$in": po_ids}}, {"material_id": {"$in": [m["id"] for m in mats]}}]})
    mdb.po_share_audit.delete_many({"po_id": {"$in": po_ids}})
    mdb.files.delete_many({"id": {"$nin": list(files_before)}, "folder": "purchase_orders"})
    mdb.materials.delete_many({"id": {"$in": [m["id"] for m in mats]}})
    mdb.sessions.delete_many({"user_id": {"$in": ids}})
    mdb.users.delete_many({"id": {"$in": ids}})
    mdb.login_attempts.delete_many({"identifier": {"$regex": "qa41_"}})


def payload(c, **kw):
    p = {"items": [{"material_id": c["mats"][0]["id"], "qty": 250, "unit_price": 50},
                   {"material_id": c["mats"][1]["id"], "qty": 3.5, "unit_price": 1000}],
         "vendor_name": "Supplier QA", "expected_date": "2026-02-01", "note": f"{TAG} note"}
    p.update(kw)
    return p


class TestCreate:
    def test_create_multiline(self, ctx):
        r = ctx["barteam"].post(f"{API}/purchase-orders", json=payload(ctx))
        assert r.status_code == 200, r.text
        d = r.json()
        ctx["pos"].append(d["id"])
        ctx["po"] = d["id"]
        assert d["status"] == "requested" and len(d["items"]) == 2
        assert d["items"][1]["qty"] == 3.5 and d["vendor_name"] == "Supplier QA"
        assert d["expected_date"] == "2026-02-01" and d["total_estimate"] == 12500 + 3500
        assert d["po_number"].startswith("PO-")
        lst = ctx["owner"].get(f"{API}/purchase-orders").json()
        assert any(p["id"] == d["id"] for p in lst)

    @pytest.mark.parametrize("bad,code", [
        ("dup", 400), ("missing", 404), ("zero", 422), ("neg", 422), ("empty", 400),
    ])
    def test_create_validation(self, ctx, bad, code):
        m0 = ctx["mats"][0]["id"]
        items = {"dup": [{"material_id": m0, "qty": 1}, {"material_id": m0, "qty": 2}],
                 "missing": [{"material_id": "nope_xyz", "qty": 1}],
                 "zero": [{"material_id": m0, "qty": 0}],
                 "neg": [{"material_id": m0, "qty": -2}],
                 "empty": []}[bad]
        r = ctx["barteam"].post(f"{API}/purchase-orders", json=payload(ctx, items=items))
        assert r.status_code == code, r.text

    def test_legacy_negative_qty_not_500(self, ctx):
        r = ctx["barteam"].post(f"{API}/purchase-orders", json={"material_id": ctx["mats"][0]["id"], "qty": -3})
        assert r.status_code in (400, 422), f"{r.status_code} {r.text[:200]}"

    def test_rider_cannot_create(self, ctx):
        r = ctx["rider"].post(f"{API}/purchase-orders", json=payload(ctx))
        assert r.status_code == 403


class TestListing:
    def test_owner_admin_all_barteam_own(self, ctx):
        r = ctx["barteam2"].post(f"{API}/purchase-orders", json=payload(ctx, note=f"{TAG} bt2"))
        assert r.status_code == 200
        ctx["pos"].append(r.json()["id"])
        ctx["po_bt2"] = r.json()["id"]
        for role in ["owner", "admin"]:
            ids = {p["id"] for p in ctx[role].get(f"{API}/purchase-orders").json()}
            assert {ctx["po"], ctx["po_bt2"]} <= ids
        bt = ctx["barteam"].get(f"{API}/purchase-orders").json()
        assert all(p["requested_by"] == ctx["users"]["barteam"]["id"] for p in bt)
        assert ctx["po_bt2"] not in {p["id"] for p in bt}
        assert ctx["rider"].get(f"{API}/purchase-orders").status_code == 403


class TestStateMachine:
    def act(self, ctx, role, decision, po=None):
        return ctx[role].post(f"{API}/purchase-orders/{po or ctx['po']}/action/{decision}", json={"note": ""})

    def test_receive_before_shipped_409(self, ctx):
        r = ctx["barteam"].post(f"{API}/purchase-orders/{ctx['po']}/receive", json={"photo": receipt_image()})
        assert r.status_code == 409

    def test_requested_stage(self, ctx):
        assert self.act(ctx, "barteam", "review").status_code == 403
        assert self.act(ctx, "owner", "approve").status_code == 403
        assert self.act(ctx, "owner", "review").status_code == 403
        assert self.act(ctx, "owner", "reject").status_code == 403
        assert self.act(ctx, "admin", "approve").status_code == 403
        assert self.act(ctx, "admin", "ship").status_code == 403
        assert self.act(ctx, "rider", "review").status_code == 403
        assert self.act(ctx, "admin", "bogus").status_code == 400
        r = self.act(ctx, "admin", "review")
        assert r.status_code == 200 and r.json()["status"] == "reviewed"

    def test_reviewed_stage(self, ctx):
        assert self.act(ctx, "admin", "review").status_code == 403
        assert self.act(ctx, "admin", "approve").status_code == 403
        assert self.act(ctx, "admin", "reject").status_code == 403
        assert self.act(ctx, "barteam", "approve").status_code == 403
        assert self.act(ctx, "owner", "ship").status_code == 403
        r = self.act(ctx, "owner", "approve")
        assert r.status_code == 200 and r.json()["status"] == "approved"

    def test_approved_stage(self, ctx):
        assert self.act(ctx, "owner", "reject").status_code == 403
        assert self.act(ctx, "barteam", "ship").status_code == 403
        r = self.act(ctx, "admin", "ship")
        assert r.status_code == 200 and r.json()["status"] == "shipped"

    def test_reject_paths(self, ctx):
        r = self.act(ctx, "admin", "reject", ctx["po_bt2"])
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        r = ctx["barteam"].post(f"{API}/purchase-orders", json=payload(ctx))
        po3 = r.json()["id"]
        ctx["pos"].append(po3)
        assert self.act(ctx, "admin", "review", po3).status_code == 200
        r = self.act(ctx, "owner", "reject", po3)
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        assert self.act(ctx, "owner", "approve", po3).status_code == 403


class TestReceive:
    def test_invalid_proofs(self, ctx):
        url = f"{API}/purchase-orders/{ctx['po']}/receive"
        assert ctx["barteam"].post(url, json={"photo": blank_image()}).status_code == 400
        assert ctx["barteam"].post(url, json={"photo": "data:image/gif;base64,R0lGODlhAQABAAAAACw="}).status_code == 400
        assert ctx["barteam"].post(url, json={"photo": "data:image/png;base64,@@@"}).status_code == 400
        assert ctx["rider"].post(url, json={"photo": receipt_image()}).status_code == 403

    def test_receive_once(self, ctx):
        before = {m["id"]: mdb.materials.find_one({"id": m["id"]})["stock"] for m in ctx["mats"]}
        r = ctx["barteam"].post(f"{API}/purchase-orders/{ctx['po']}/receive", json={"photo": receipt_image("JPEG"), "received_note": "ok"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "arrived"
        assert "arrival_proof_data" not in d
        assert d["arrival_proof"].startswith("/api/") and "base64" not in d["arrival_proof"]
        ctx["proof_url"] = d["arrival_proof"]
        after = {m["id"]: mdb.materials.find_one({"id": m["id"]})["stock"] for m in ctx["mats"]}
        assert after[ctx["mats"][0]["id"]] == before[ctx["mats"][0]["id"]] + 250
        assert after[ctx["mats"][1]["id"]] == before[ctx["mats"][1]["id"]] + 3.5
        txs = list(mdb.inventory_tx.find({"purchase_order_id": ctx["po"]}))
        assert len(txs) == 2 and all(t["type"] == "in" for t in txs)
        r2 = ctx["admin"].post(f"{API}/purchase-orders/{ctx['po']}/receive", json={"photo": receipt_image("WEBP")})
        assert r2.status_code == 409
        again = {m["id"]: mdb.materials.find_one({"id": m["id"]})["stock"] for m in ctx["mats"]}
        assert again == after
        assert mdb.inventory_tx.count_documents({"purchase_order_id": ctx["po"]}) == 2

    def test_proof_access(self, ctx):
        url = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + ctx["proof_url"]
        assert requests.get(url).status_code == 401
        assert ctx["rider"].get(url).status_code == 403
        for role in ["owner", "admin", "barteam"]:
            r = ctx[role].get(url)
            assert r.status_code == 200 and r.headers["content-type"].startswith("image/")
            assert "no-store" in r.headers.get("cache-control", "")

    def test_listing_never_has_proof_data(self, ctx):
        for role in ["owner", "admin", "barteam"]:
            for p in ctx[role].get(f"{API}/purchase-orders").json():
                assert "arrival_proof_data" not in p
                assert not str(p.get("arrival_proof") or "").startswith("data:")


class TestShareIntent:
    def test_share_intent(self, ctx):
        r = ctx["barteam"].post(f"{API}/purchase-orders/{ctx['po']}/share-intent")
        assert r.status_code == 200 and r.json()["recipient"] == "6281283578212"
        assert ctx["barteam"].post(f"{API}/purchase-orders/{ctx['po_bt2']}/share-intent").status_code == 404
        assert ctx["rider"].post(f"{API}/purchase-orders/{ctx['po']}/share-intent").status_code == 403
        assert requests.post(f"{API}/purchase-orders/{ctx['po']}/share-intent").status_code == 401
