# Iteration 32: /api/reports/sales filters, KPIs, bundle allocation, HPP/profit/share, transaction rows; Rider forbidden;
# Deposit regression (overcount 400, single notification on resave, no *_auto flags).
# Run: pytest tests/test_iter32_sales_report.py -n 0   (seeds TEST_ data in Mongo, hard-deletes at teardown)
import os
import uuid
from datetime import datetime, timedelta, timezone
import jwt
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

DATE = "2030-02-10"
AMERICANO = "6cc0ca7c-b6f4-4b0c-b6e6-c21707d4e4e4"  # 8000
KOPSU = "c9750dec-4968-4cd2-be2b-0695eb0bafe7"  # 10000
CREAMY = "6c5553d9-8c31-4a73-8348-c3e4b1c819f5"  # 12000
MATCHA = "d108663a-f470-44aa-88fe-4ff80c7e46e8"  # 12000
RA = "TEST_rA_" + uuid.uuid4().hex[:6]
RB = "TEST_rB_" + uuid.uuid4().hex[:6]
S1, S2, S3 = ("TEST_s1_" + uuid.uuid4().hex[:6], "TEST_s2_" + uuid.uuid4().hex[:6], "TEST_s3_" + uuid.uuid4().hex[:6])


def cleanup():
    ids = [RA, RB]
    dep_ids = [d["id"] for d in db.deposits.find({"rider_id": {"$in": ids}})]
    db.notifications.delete_many({"ref_id": {"$in": dep_ids}})
    for c in ("deposits", "sales", "eod", "rider_stock", "menu_stock_tx"):
        db[c].delete_many({"rider_id": {"$in": ids}})
    db.sessions.delete_many({"user_id": {"$in": ids}})
    db.users.delete_many({"id": {"$in": ids}})


@pytest.fixture(scope="module", autouse=True)
def seed():
    cleanup()
    for rid, name in ((RA, "TEST_Rider A"), (RB, "TEST_Rider B")):
        db.users.insert_one({"id": rid, "name": name, "username": rid, "role": "rider", "active": True, "created_at": "2030-01-01"})
    db.sales.insert_many([
        {"id": S1, "rider_id": RA, "rider_name": "TEST_Rider A", "receipt_no": "TEST-1", "date": DATE, "time": "08:15", "total": 16000, "cups": 2,
         "payment_method": "cash", "payment_parts": [], "order_type": "takeaway",
         "items": [{"menu_id": AMERICANO, "name": "SI AMERICANO", "qty": 2, "price": 8000, "subtotal": 16000}]},
        {"id": S2, "rider_id": RA, "rider_name": "TEST_Rider A", "receipt_no": "TEST-2", "date": DATE, "time": "09:30", "total": 22000, "cups": 2,
         "payment_method": "qris", "payment_parts": [], "order_type": "dine_in",
         "items": [{"menu_id": KOPSU, "name": "SI KOPSU AREN", "qty": 1, "price": 10000, "subtotal": 10000},
                   {"menu_id": CREAMY, "name": "SI CREAMY LATTE", "qty": 1, "price": 12000, "subtotal": 12000}]},
        {"id": S3, "rider_id": RB, "rider_name": "TEST_Rider B", "receipt_no": "TEST-3", "date": DATE, "time": "09:45", "total": 45000, "cups": 4,
         "payment_method": "split", "payment_parts": [{"method": "cash", "amount": 20000}, {"method": "qris", "amount": 25000}], "order_type": "online",
         "items": [{"menu_id": None, "bundle": 1, "name": "BUNDLING 1 (4 cups)", "qty": 1, "price": 45000, "subtotal": 45000,
                    "components": {CREAMY: 2, MATCHA: 2}, "component_names": {"SI CREAMY LATTE": 2, "SI MATCHA": 2}}]},
    ])
    yield
    cleanup()


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": r.json()["account_token"], "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def costs(client):
    return {m["id"]: m["cost"] for m in client.get(f"{BASE_URL}/api/menus").json()}


def rep(client, **params):
    r = client.get(f"{BASE_URL}/api/reports/sales", params={"start": DATE, "end": DATE, **params})
    assert r.status_code == 200, r.text
    def keys(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield k
                yield from keys(v)
        elif isinstance(o, list):
            for v in o:
                yield from keys(v)
    assert "_id" not in set(keys(r.json()))
    return r.json()


def prod(d, name):
    return next(p for p in d["products"] if p["name"] == name)


class TestSalesReportAll:
    def test_totals(self, client):
        d = rep(client)
        assert d["transactions"] == 3 and d["revenue"] == 83000 and d["total_cups"] == 8
        assert d["average_order"] == round(83000 / 3)
        pay = {p["name"]: p["value"] for p in d["payment_distribution"]}
        assert pay == {"CASH": 36000, "QRIS": 47000}
        assert {o["name"]: o["value"] for o in d["order_distribution"]} == {"regular": 38000, "bundling": 45000}
        assert {o["name"]: o["value"] for o in d["service_distribution"]} == {"takeaway": 16000, "dine_in": 22000, "online": 45000}
        hours = {h["hour"]: (h["transactions"], h["revenue"]) for h in d["hourly"]}
        assert hours == {"08:00": (1, 16000), "09:00": (2, 67000)}
        assert d["daily_revenue"] == [{"date": DATE, "revenue": 83000}]

    def test_products_bundle_allocation_hpp(self, client, costs):
        d = rep(client)
        cr, ma = prod(d, "SI CREAMY LATTE"), prod(d, "SI MATCHA")
        assert cr["qty"] == 3 and cr["revenue"] == 34500
        assert ma["qty"] == 2 and ma["revenue"] == 22500
        assert prod(d, "SI AMERICANO")["revenue"] == 16000 and prod(d, "SI KOPSU AREN")["revenue"] == 10000
        assert cr["hpp"] == round(costs[CREAMY] * 3) and cr["profit"] == cr["revenue"] - cr["hpp"]
        assert cr["share"] == round(34500 / 83000 * 100, 1)
        assert sum(p["revenue"] for p in d["products"]) == 83000
        assert [p["rank"] for p in d["products"]] == [1, 2, 3, 4] and d["products"][0]["name"] == "SI CREAMY LATTE"
        assert d["top_product"]["name"] == "SI CREAMY LATTE"

    def test_transaction_rows(self, client):
        d = rep(client)
        rows = {t["id"]: t for t in d["transaction_rows"]}
        assert set(rows) == {S1, S2, S3}
        assert rows[S3]["cash"] == 20000 and rows[S3]["qris"] == 25000 and rows[S3]["total"] == 45000
        assert rows[S3]["sale_kind"] == "bundling" and rows[S3]["order_type"] == "online" and rows[S3]["rider_id"] == RB
        assert rows[S1]["total"] == 16000 and rows[S1]["cups"] == 2
        # per-row payment split must come from each sale (regression: stale `payments` variable leaked last sale's split)
        assert (rows[S1]["cash"], rows[S1]["qris"]) == (16000, 0)
        assert (rows[S2]["cash"], rows[S2]["qris"]) == (0, 22000)
        assert sum(t["total"] for t in d["transaction_rows"]) == d["revenue"]


class TestSalesReportFilters:
    def test_payment_qris(self, client):
        d = rep(client, payment_method="qris")
        assert d["transactions"] == 2 and d["revenue"] == 47000
        assert {t["id"] for t in d["transaction_rows"]} == {S2, S3}
        assert next(t for t in d["transaction_rows"] if t["id"] == S3)["total"] == 25000
        assert prod(d, "SI CREAMY LATTE")["revenue"] == 12000 + 12500 and prod(d, "SI MATCHA")["revenue"] == 12500
        assert "SI AMERICANO" not in [p["name"] for p in d["products"]]

    def test_payment_cash(self, client):
        d = rep(client, payment_method="cash")
        assert d["transactions"] == 2 and d["revenue"] == 36000
        assert {t["id"] for t in d["transaction_rows"]} == {S1, S3}

    def test_payment_filter_distribution_consistency(self, client):
        # Informational: payment_distribution under qris filter should arguably only include QRIS
        d = rep(client, payment_method="qris")
        pay = {p["name"]: p["value"] for p in d["payment_distribution"]}
        print("QRIS-filter payment_distribution:", pay, "total_cups:", d["total_cups"])
        assert pay.get("QRIS") == 47000

    def test_sale_kind(self, client):
        b = rep(client, sale_kind="bundling")
        assert b["transactions"] == 1 and b["revenue"] == 45000 and b["total_cups"] == 4
        assert {p["name"] for p in b["products"]} == {"SI CREAMY LATTE", "SI MATCHA"}
        r = rep(client, sale_kind="regular")
        assert r["transactions"] == 2 and r["revenue"] == 38000
        assert {t["id"] for t in r["transaction_rows"]} == {S1, S2}
        # legacy alias
        assert rep(client, order_type="bundling")["revenue"] == 45000

    def test_service_type(self, client):
        assert [t["id"] for t in rep(client, service_type="dine_in")["transaction_rows"]] == [S2]
        assert [t["id"] for t in rep(client, service_type="online")["transaction_rows"]] == [S3]
        assert [t["id"] for t in rep(client, service_type="takeaway")["transaction_rows"]] == [S1]

    def test_rider(self, client):
        d = rep(client, rider_id=RB)
        assert d["revenue"] == 45000 and [t["id"] for t in d["transaction_rows"]] == [S3]
        d = rep(client, rider_id=RA, payment_method="qris")
        assert d["revenue"] == 22000 and [t["id"] for t in d["transaction_rows"]] == [S2]
        assert rep(client, rider_id="all")["revenue"] == 83000

    def test_all_values_noop(self, client):
        d = rep(client, payment_method="all", sale_kind="all", service_type="all", rider_id="all")
        assert d["revenue"] == 83000

    def test_empty_range(self, client):
        r = client.get(f"{BASE_URL}/api/reports/sales", params={"start": "2031-01-01", "end": "2031-01-02"})
        assert r.status_code == 200 and r.json()["revenue"] == 0 and r.json()["transaction_rows"] == []


class TestSalesReportAuth:
    def test_rider_forbidden(self):
        session_id = "TEST_session_" + uuid.uuid4().hex[:8]
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        db.sessions.insert_one({
            "id": session_id,
            "user_id": RA,
            "expires_at": expires_at,
            "revoked": False,
        })
        tok = jwt.encode(
            {"sub": RA, "sid": session_id, "exp": expires_at, "type": "access"},
            os.environ["JWT_SECRET"],
            algorithm="HS256",
        )
        r = requests.get(f"{BASE_URL}/api/reports/sales", params={"start": DATE, "end": DATE}, headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 403

    def test_unauthenticated(self):
        r = requests.get(f"{BASE_URL}/api/reports/sales", params={"start": DATE, "end": DATE})
        assert r.status_code == 401


class TestDepositRegression:
    def test_overcount_rejected_and_single_notification(self, client):
        db.rider_stock.insert_one({"id": uuid.uuid4().hex, "rider_id": RA, "date": "2030-02-11", "items": {AMERICANO: 10}, "verified_at": "2030-02-11T00:00:00"})
        db.eod.insert_one({"rider_id": RA, "date": "2030-02-11", "closed_by": "TEST", "time": "20:00"})
        bad = {"rider_id": RA, "date": "2030-02-11", "rows": [{"menu_id": AMERICANO, "stock": 2, "cash": 3, "qris": 0, "remaining": 0, "wastage": 0}]}
        r = client.post(f"{BASE_URL}/api/deposits", json=bad)
        assert r.status_code == 400 and "melebihi" in r.json()["detail"]
        assert db.deposits.count_documents({"rider_id": RA}) == 0
        good = {"rider_id": RA, "date": "2030-02-11", "rows": [{"menu_id": AMERICANO, "stock": 6, "cash": 3, "qris": 2, "remaining": 1, "wastage": 0, "cash_auto": True, "qris_auto": True}]}
        for _ in range(3):
            r = client.post(f"{BASE_URL}/api/deposits", json=good)
            assert r.status_code == 200, r.text
        dep = db.deposits.find_one({"rider_id": RA, "date": "2030-02-11"}, {"_id": 0})
        assert db.notifications.count_documents({"ref_id": dep["id"]}) == 1
        assert all("cash_auto" not in row and "qris_auto" not in row for row in dep["rows"])
        assert dep["total_cash"] == 24000 and dep["total_qris"] == 16000
