# Iter18: POS P0 - order type (Dine In/Takeaway/Online), table number, split payment, stock-gated payment,
# rider PIN attendance, split accounting in EOD / reports / daily summaries. All QA data cleaned via Mongo at teardown.
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
TEST_DATE = "2030-01-15"
RIDER_PIN = "246813"
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
    menu_snapshot = {m["id"]: m.get("stock", 0) for m in mdb.menus.find({}, {"_id": 0, "id": 1, "stock": 1})}
    owner = _login("baa", "130994")
    uname = f"qa_rider_p0_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/users", headers=owner, json={"name": "TEST QA Rider P0", "username": uname, "role": "rider", "pin": RIDER_PIN})
    assert r.status_code == 200, r.text
    rider = r.json()
    rider_h = _login(uname, RIDER_PIN)
    menus = list(mdb.menus.find({}, {"_id": 0, "id": 1, "price": 1, "name": 1}))
    m12 = [m for m in menus if m["price"] == 12000]
    other = [m for m in menus if m["price"] != 12000][0]
    data = {"owner": owner, "rider": rider, "rider_h": rider_h, "m12": m12, "other": other, "sales": []}
    yield data
    # Cleanup
    rid = rider["id"]
    mdb.sales.delete_many({"rider_id": rid})
    mdb.rider_stock.delete_many({"rider_id": rid})
    mdb.attendance.delete_many({"rider_id": rid})
    mdb.eod.delete_many({"rider_id": rid})
    mdb.gps.delete_many({"rider_id": rid})
    mdb.customers.delete_many({"name": {"$regex": "^TEST_"}})
    mdb.files.delete_many({"user_id": rid})
    mdb.login_attempts.delete_many({"identifier": {"$regex": rid}})
    mdb.users.delete_one({"id": rid})
    for mid, st in menu_snapshot.items():
        mdb.menus.update_one({"id": mid}, {"$set": {"stock": st}})


def _sale(ctx, **kw):
    body = {"rider_id": ctx["rider"]["id"], "date": TEST_DATE, "items": [{"menu_id": ctx["other"]["id"], "qty": 1}],
            "payment_method": "cash", "payment_parts": [], "cash_received": 0, "order_type": "takeaway", "table_number": ""}
    body.update(kw)
    return requests.post(f"{API}/sales", headers=ctx["rider_h"], json=body)


# --- Stock gate: products visible but payment blocked before verification
def test_01_stock_unverified_blocks_sale(ctx):
    items = {ctx["other"]["id"]: 20, **{m["id"]: 10 for m in ctx["m12"][:2]}}
    r = requests.post(f"{API}/rider-stock", headers=ctx["owner"], json={"rider_id": ctx["rider"]["id"], "date": TEST_DATE, "items": items, "photo": PHOTO})
    assert r.status_code == 200, r.text
    ctx["stock_id"] = r.json()["id"]
    st = requests.get(f"{API}/pos/stock", headers=ctx["owner"], params={"rider_id": ctx["rider"]["id"], "date": TEST_DATE}).json()
    assert st["has_stock"] is False and st["pending_stock"] is True
    assert len(st["items"]) >= 1
    r = _sale(ctx, cash_received=100000)
    assert r.status_code == 400 and "stock" in r.text.lower()


def test_02_rider_verifies_stock(ctx):
    r = requests.post(f"{API}/rider-stock/{ctx['stock_id']}/verify", headers=ctx["rider_h"])
    assert r.status_code == 200 and r.json()["verified_at"]
    st = requests.get(f"{API}/pos/stock", headers=ctx["rider_h"], params={"rider_id": ctx["rider"]["id"], "date": TEST_DATE}).json()
    assert st["has_stock"] is True


# --- Validation of order type / table / payment
def test_03_dine_in_requires_table(ctx):
    r = _sale(ctx, order_type="dine_in", table_number="  ", cash_received=100000)
    assert r.status_code == 400 and "meja" in r.text.lower()


def test_04_invalid_order_type(ctx):
    r = _sale(ctx, order_type="delivery", cash_received=100000)
    assert r.status_code == 400


def test_05_split_sum_mismatch(ctx):
    p = ctx["other"]["price"]
    r = _sale(ctx, payment_parts=[{"method": "cash", "amount": 1000}, {"method": "qris", "amount": p}], cash_received=1000)
    assert r.status_code == 400 and "total" in r.text.lower()


def test_06_invalid_method_and_nonpositive_part(ctx):
    p = ctx["other"]["price"]
    assert _sale(ctx, payment_method="bitcoin", cash_received=p).status_code == 400
    assert _sale(ctx, payment_parts=[{"method": "ovo", "amount": p}]).status_code == 400
    assert _sale(ctx, payment_parts=[{"method": "cash", "amount": p + 1000}, {"method": "qris", "amount": -1000}], cash_received=p + 1000).status_code == 400


def test_07_insufficient_cash(ctx):
    p = ctx["other"]["price"]
    assert _sale(ctx, cash_received=p - 1).status_code == 400
    # split with cash_received less than cash part
    assert _sale(ctx, payment_parts=[{"method": "cash", "amount": p / 2}, {"method": "qris", "amount": p / 2}], cash_received=1).status_code == 400


# --- Successful sales
def test_08_split_dine_in_sale_persisted(ctx):
    m = ctx["m12"][0]
    r = _sale(ctx, items=[{"menu_id": m["id"], "qty": 2}], payment_method="cash",
              payment_parts=[{"method": "cash", "amount": 5000}, {"method": "qris", "amount": 19000}],
              cash_received=5000, order_type="dine_in", table_number="7", customer_name="TEST_split", client_id=str(uuid.uuid4()))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["payment_method"] == "split"
    assert d["payment_parts"] == [{"method": "cash", "amount": 5000}, {"method": "qris", "amount": 19000}]
    assert d["order_type"] == "dine_in" and d["table_number"] == "7" and d["total"] == 24000 and d["change"] == 0
    rows = requests.get(f"{API}/sales", headers=ctx["owner"], params={"start": TEST_DATE, "end": TEST_DATE, "rider_id": ctx["rider"]["id"]}).json()
    got = [s for s in rows if s["id"] == d["id"]][0]
    assert got["payment_method"] == "split" and got["table_number"] == "7" and got["order_type"] == "dine_in"


def test_09_cash_and_qris_and_online(ctx):
    p = ctx["other"]["price"]
    r1 = _sale(ctx, cash_received=p + 2000, order_type="takeaway")
    assert r1.status_code == 200, r1.text
    assert r1.json()["change"] == 2000 and r1.json()["payment_parts"] == [{"method": "cash", "amount": p}]
    r2 = _sale(ctx, payment_method="qris", order_type="online", table_number="9")
    assert r2.status_code == 200, r2.text
    assert r2.json()["payment_method"] == "qris" and r2.json()["table_number"] == "" and r2.json()["order_type"] == "online"
    # bundle split (4 cups 45000): 20000 cash / 25000 qris
    a, b = ctx["m12"][0]["id"], ctx["m12"][1]["id"]
    r3 = _sale(ctx, items=[{"bundle": 1, "qty": 1, "components": {a: 2, b: 2}}],
               payment_parts=[{"method": "cash", "amount": 20000}, {"method": "qris", "amount": 25000}], cash_received=20000)
    assert r3.status_code == 200, r3.text
    ctx["expected"] = {"cash": 5000 + p + 20000, "qris": 19000 + p + 25000, "total": 24000 + 2 * p + 45000}


def test_10_client_id_idempotent(ctx):
    cid = str(uuid.uuid4())
    p = ctx["other"]["price"]
    r1 = _sale(ctx, cash_received=p, client_id=cid)
    r2 = _sale(ctx, cash_received=p, client_id=cid)
    assert r1.status_code == 200 and r2.status_code == 200 and r1.json()["id"] == r2.json()["id"]
    ctx["expected"]["cash"] += p
    ctx["expected"]["total"] += p


# --- Accounting
def test_11_eod_split_totals(ctx):
    e = requests.get(f"{API}/sales/eod", headers=ctx["owner"], params={"rider_id": ctx["rider"]["id"], "date": TEST_DATE}).json()
    exp = ctx["expected"]
    assert e["transactions"] == 5
    assert abs(e["total_cash"] - exp["cash"]) < 0.01, e["total_cash"]
    assert abs(e["total_qris"] - exp["qris"]) < 0.01, e["total_qris"]
    assert abs(e["total"] - exp["total"]) < 0.01


def test_12_reports_sales_filters(ctx):
    exp = ctx["expected"]
    q = {"start": TEST_DATE, "end": TEST_DATE}
    all_ = requests.get(f"{API}/reports/sales", headers=ctx["owner"], params={**q, "payment_method": "all"})
    assert all_.status_code == 200, all_.text
    cash = requests.get(f"{API}/reports/sales", headers=ctx["owner"], params={**q, "payment_method": "cash"}).json()
    qris = requests.get(f"{API}/reports/sales", headers=ctx["owner"], params={**q, "payment_method": "qris"}).json()
    A = all_.json()
    ctx["report_keys"] = list(A.keys())
    tot = lambda d: d["revenue"]
    assert A["transactions"] == 5 and cash["transactions"] == 4 and qris["transactions"] == 3
    dist = {x["name"]: x["value"] for x in A["payment_distribution"]}
    assert abs(dist["CASH"] - exp["cash"]) < 0.01 and abs(dist["QRIS"] - exp["qris"]) < 0.01
    assert abs(sum(x["revenue"] for x in A["daily_revenue"]) - exp["total"]) < 0.01
    assert abs(tot(A) - exp["total"]) < 0.01, A.keys()
    assert abs(tot(cash) - exp["cash"]) < 0.01
    assert abs(tot(qris) - exp["qris"]) < 0.01
    assert abs(tot(cash) + tot(qris) - tot(A)) < 0.01


def test_13_dashboard_daily_summary(ctx):
    r = requests.get(f"{API}/dashboard/summary", headers=ctx["owner"], params={"start": TEST_DATE, "end": TEST_DATE, "rider_id": ctx["rider"]["id"]})
    assert r.status_code == 200, r.text
    ctx["dash"] = r.json()
    br = [x for x in r.json().get("by_rider", []) if x.get("rider_id") == ctx["rider"]["id"]]
    if br:
        assert abs(br[0]["cash"] - ctx["expected"]["cash"]) < 0.01 and abs(br[0]["qris"] - ctx["expected"]["qris"]) < 0.01
    else:
        print("DASH KEYS", list(r.json().keys()))
    rr = requests.get(f"{API}/rider-rank", headers=ctx["owner"], params={"start": TEST_DATE, "end": TEST_DATE, "rider_id": ctx["rider"]["id"]}).json()
    assert abs(rr["gross"] - ctx["expected"]["total"]) < 0.01


# --- Attendance PIN
def test_14_checkin_wrong_pin_rejected(ctx):
    r = requests.post(f"{API}/attendance/checkin", headers=ctx["owner"], json={"rider_id": ctx["rider"]["id"], "pin": "000000", "photo": PHOTO, "date": TEST_DATE})
    assert r.status_code == 401
    r = requests.post(f"{API}/attendance/checkin", headers=ctx["owner"], json={"rider_id": ctx["rider"]["id"], "pin": "", "photo": PHOTO, "date": TEST_DATE})
    assert r.status_code == 401


def test_15_checkin_correct_pin(ctx):
    r = requests.post(f"{API}/attendance/checkin", headers=ctx["owner"], json={"rider_id": ctx["rider"]["id"], "pin": RIDER_PIN, "photo": PHOTO, "date": TEST_DATE})
    assert r.status_code == 200, r.text
    assert r.json()["rider_id"] == ctx["rider"]["id"]
    r2 = requests.post(f"{API}/attendance/checkin", headers=ctx["owner"], json={"rider_id": ctx["rider"]["id"], "pin": RIDER_PIN, "photo": PHOTO, "date": TEST_DATE})
    assert r2.status_code == 409


def test_16_eod_close_blocks_sales(ctx):
    r = requests.post(f"{API}/sales/eod/close", headers=ctx["rider_h"], json={"rider_id": ctx["rider"]["id"], "date": TEST_DATE})
    assert r.status_code == 200 and r.json()["closed"] is True
    assert _sale(ctx, cash_received=100000).status_code == 400
