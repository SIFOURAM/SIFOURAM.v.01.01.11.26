# Iter19: Rider stock handoff/acceptance photo verification, POS stock gating, remaining stock endpoint,
# rider isolation. All QA data removed via Mongo at teardown (rider, stock, sales, files, attendance, eod, gps, login_attempts) + menu stock restore.
import os
import uuid
import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
TEST_DATE = "2030-02-20"
PIN = "246813"
PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(identifier, pin):
    r = requests.post(f"{API}/auth/identify", json={"identifier": identifier, "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    r = requests.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": pin, "remember": True})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def ctx():
    snap = {m["id"]: m.get("stock", 0) for m in mdb.menus.find({}, {"_id": 0, "id": 1, "stock": 1})}
    files_before = set(f["id"] for f in mdb.files.find({}, {"_id": 0, "id": 1}))
    owner = _login("baa", "130994")
    riders, unames = [], []
    for i in range(2):
        un = f"qa_rider19_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/users", headers=owner, json={"name": f"TEST QA Rider19 {i}", "username": un, "role": "rider", "pin": PIN})
        assert r.status_code == 200, r.text
        riders.append(r.json())
        unames.append(un)
    rh = [_login(u, PIN) for u in unames]
    menus = list(mdb.menus.find({}, {"_id": 0, "id": 1, "price": 1, "name": 1}))
    d = {"owner": owner, "riders": riders, "rh": rh, "menus": menus}
    yield d
    ids = [r["id"] for r in riders]
    for c in ["sales", "rider_stock", "attendance", "eod", "gps", "deposits"]:
        mdb[c].delete_many({"rider_id": {"$in": ids}})
    mdb.files.delete_many({"id": {"$nin": list(files_before)}})
    mdb.customers.delete_many({"name": {"$regex": "^TEST_"}})
    for u in unames + ids:
        mdb.login_attempts.delete_many({"identifier": {"$regex": u}})
    mdb.users.delete_many({"id": {"$in": ids}})
    for mid, v in snap.items():
        mdb.menus.update_one({"id": mid}, {"$set": {"stock": v}})


# --- Owner creates stock with photo -> pending
def test_01_owner_create_stock_pending(ctx):
    m = ctx["menus"]
    items = {m[0]["id"]: 5, m[1]["id"]: 3}
    r = requests.post(f"{API}/rider-stock", headers=ctx["owner"], json={"rider_id": ctx["riders"][0]["id"], "date": TEST_DATE, "items": items, "photo": PHOTO})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["total"] == 8 and s["verified_at"] is None and s["photo"]
    ctx["stock"] = s
    st = requests.get(f"{API}/pos/stock", headers=ctx["rh"][0], params={"rider_id": ctx["riders"][0]["id"], "date": TEST_DATE}).json()
    assert st["has_stock"] is False and st["pending_stock"] is True


def test_02_stock_without_photo_rejected(ctx):
    r = requests.post(f"{API}/rider-stock", headers=ctx["owner"], json={"rider_id": ctx["riders"][1]["id"], "date": TEST_DATE, "items": {ctx["menus"][0]["id"]: 1}})
    assert r.status_code == 400


def test_03_sale_blocked_before_verify(ctx):
    r = requests.post(f"{API}/sales", headers=ctx["rh"][0], json={"rider_id": ctx["riders"][0]["id"], "date": TEST_DATE, "items": [{"menu_id": ctx["menus"][0]["id"], "qty": 1}], "payment_method": "cash"})
    assert r.status_code == 400


# --- Rider isolation on GET
def test_04_rider_sees_only_own(ctx):
    r = requests.get(f"{API}/rider-stock", headers=ctx["rh"][1], params={"rider_id": ctx["riders"][0]["id"], "date": TEST_DATE})
    assert r.status_code == 403
    r = requests.get(f"{API}/rider-stock", headers=ctx["rh"][0], params={"rider_id": ctx["riders"][0]["id"], "date": TEST_DATE})
    assert r.status_code == 200 and r.json()["id"] == ctx["stock"]["id"]
    h = requests.get(f"{API}/rider-stock/history", headers=ctx["rh"][1], params={"start": "2000-01-01", "end": "2100-01-01", "rider_id": ctx["riders"][0]["id"]}).json()
    assert all(x["rider_id"] == ctx["riders"][1]["id"] for x in h)


# --- Verify requires photo body
def test_05_verify_without_photo_422(ctx):
    sid = ctx["stock"]["id"]
    assert requests.post(f"{API}/rider-stock/{sid}/verify", headers=ctx["rh"][0]).status_code == 422
    assert requests.post(f"{API}/rider-stock/{sid}/verify", headers=ctx["rh"][0], json={}).status_code == 422


def test_06_verify_empty_or_non_image_photo(ctx):
    sid = ctx["stock"]["id"]
    r = requests.post(f"{API}/rider-stock/{sid}/verify", headers=ctx["rh"][0], json={"photo": ""})
    print("empty photo status", r.status_code, r.text[:200])
    ok_empty = r.status_code in (400, 422)
    if not ok_empty:
        mdb.rider_stock.update_one({"id": sid}, {"$set": {"verified_at": None, "verified_by": None, "verified_by_name": None, "verification_photo": None}})
    r2 = requests.post(f"{API}/rider-stock/{sid}/verify", headers=ctx["rh"][0], json={"photo": "hello"})
    print("non-image photo status", r2.status_code, r2.text[:200])
    ok_text = r2.status_code in (400, 422)
    if not ok_text:
        mdb.rider_stock.update_one({"id": sid}, {"$set": {"verified_at": None, "verified_by": None, "verified_by_name": None, "verification_photo": None}})
    assert ok_empty and ok_text, f"empty={r.status_code} text={r2.status_code}"


def test_07_other_rider_and_owner_cannot_verify(ctx):
    sid = ctx["stock"]["id"]
    assert requests.post(f"{API}/rider-stock/{sid}/verify", headers=ctx["rh"][1], json={"photo": PHOTO}).status_code == 404
    assert requests.post(f"{API}/rider-stock/{sid}/verify", headers=ctx["owner"], json={"photo": PHOTO}).status_code == 403
    assert mdb.rider_stock.find_one({"id": sid})["verified_at"] is None


def test_08_rider_verify_with_photo(ctx):
    sid = ctx["stock"]["id"]
    r = requests.post(f"{API}/rider-stock/{sid}/verify", headers=ctx["rh"][0], json={"photo": PHOTO})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["verified_at"] and d["verified_by"] == ctx["riders"][0]["id"]
    assert d["verified_by_name"] == "TEST QA Rider19 0" and d["verification_photo"]
    print("verification_photo prefix:", d["verification_photo"][:40])
    st = requests.get(f"{API}/pos/stock", headers=ctx["rh"][0], params={"rider_id": ctx["riders"][0]["id"], "date": TEST_DATE}).json()
    assert st["has_stock"] is True and st["pending_stock"] is False
    first = [i for i in st["items"] if i["menu_id"] == ctx["menus"][0]["id"]][0]
    assert first["initial"] == 5 and first["remaining"] == 5
    # idempotent re-verify keeps original
    r2 = requests.post(f"{API}/rider-stock/{sid}/verify", headers=ctx["rh"][0], json={"photo": PHOTO})
    assert r2.status_code == 200 and r2.json()["verified_at"] == d["verified_at"]


# --- Sales and remaining consistency
def test_09_sale_and_remaining(ctx):
    rid = ctx["riders"][0]["id"]
    m0 = ctx["menus"][0]["id"]
    r = requests.post(f"{API}/sales", headers=ctx["rh"][0], json={"rider_id": rid, "date": TEST_DATE, "items": [{"menu_id": m0, "qty": 2}], "payment_method": "cash", "cash_received": 1000000, "client_id": f"qa19-{uuid.uuid4().hex}"})
    assert r.status_code == 200, r.text
    rows = requests.get(f"{API}/rider-stock/remaining", headers=ctx["owner"], params={"date": TEST_DATE}).json()
    row = [x for x in rows if x["rider_id"] == rid][0]
    assert row["initial_total"] == 8 and row["sold_total"] == 2 and row["remaining_total"] == 6
    it = [i for i in row["items"] if i["menu_id"] == m0][0]
    assert it["initial"] == 5 and it["sold"] == 2 and it["remaining"] == 3
    st = requests.get(f"{API}/pos/stock", headers=ctx["owner"], params={"rider_id": rid, "date": TEST_DATE}).json()
    assert [i for i in st["items"] if i["menu_id"] == m0][0]["remaining"] == 3


def test_10_remaining_rider_scoped(ctx):
    # create pending stock for rider 1 too
    r = requests.post(f"{API}/rider-stock", headers=ctx["owner"], json={"rider_id": ctx["riders"][1]["id"], "date": TEST_DATE, "items": {ctx["menus"][0]["id"]: 4}, "photo": PHOTO})
    assert r.status_code == 200
    own = requests.get(f"{API}/rider-stock/remaining", headers=ctx["owner"], params={"date": TEST_DATE}).json()
    assert len([x for x in own if x["rider_id"] in (ctx["riders"][0]["id"], ctx["riders"][1]["id"])]) == 2
    filt = requests.get(f"{API}/rider-stock/remaining", headers=ctx["owner"], params={"date": TEST_DATE, "rider_id": ctx["riders"][1]["id"]}).json()
    assert len(filt) == 1 and filt[0]["rider_id"] == ctx["riders"][1]["id"]
    r1 = requests.get(f"{API}/rider-stock/remaining", headers=ctx["rh"][1], params={"date": TEST_DATE, "rider_id": ctx["riders"][0]["id"]}).json()
    assert len(r1) == 1 and r1[0]["rider_id"] == ctx["riders"][1]["id"]
    # pending stock row: initial_total says 4 but remaining computed from unverified = 0
    print("pending row:", r1[0]["initial_total"], r1[0]["sold_total"], r1[0]["remaining_total"], r1[0]["verified_at"])


def test_11_pending_row_consistency(ctx):
    r1 = requests.get(f"{API}/rider-stock/remaining", headers=ctx["rh"][1], params={"date": TEST_DATE}).json()[0]
    assert r1["initial_total"] - r1["sold_total"] == r1["remaining_total"], f"pending row inconsistent: {r1['initial_total']}/{r1['sold_total']}/{r1['remaining_total']}"


def test_12_rider_cannot_read_other_pos_stock(ctx):
    r = requests.get(f"{API}/pos/stock", headers=ctx["rh"][1], params={"rider_id": ctx["riders"][0]["id"], "date": TEST_DATE})
    print("rider1 reading rider0 pos stock:", r.status_code)
    assert r.status_code == 403


def test_13_owner_edit_after_verify_keeps_verified(ctx):
    # Observational: does owner editing verified stock require re-verification?
    m = ctx["menus"]
    r = requests.post(f"{API}/rider-stock", headers=ctx["owner"], json={"rider_id": ctx["riders"][0]["id"], "date": TEST_DATE, "items": {m[0]["id"]: 5, m[1]["id"]: 10}})
    assert r.status_code == 200, r.text
    doc = mdb.rider_stock.find_one({"id": ctx["stock"]["id"]})
    print("after owner edit verified_at:", doc.get("verified_at"), "total:", doc["total"])
