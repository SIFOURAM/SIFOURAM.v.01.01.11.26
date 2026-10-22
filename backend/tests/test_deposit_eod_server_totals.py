# Setoran/Deposit: server-side EOD-derived totals, forged-field rejection, EOD-closed gate (iteration 30)
# Seeds a TEST_ temporary rider + sales + rider_stock directly in Mongo and hard-deletes everything at teardown.
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

DATE = "2030-01-15"
AMERICANO = "6cc0ca7c-b6f4-4b0c-b6e6-c21707d4e4e4"
KOPSU = "c9750dec-4968-4cd2-be2b-0695eb0bafe7"
CREAMY = "6c5553d9-8c31-4a73-8348-c3e4b1c819f5"
RIDER_ID = "TEST_rider_" + uuid.uuid4().hex[:8]


def cleanup():
    dep_ids = [d["id"] for d in db.deposits.find({"rider_id": RIDER_ID})]
    db.notifications.delete_many({"ref_id": {"$in": dep_ids}})
    db.deposits.delete_many({"rider_id": RIDER_ID})
    db.sales.delete_many({"rider_id": RIDER_ID})
    db.eod.delete_many({"rider_id": RIDER_ID})
    db.rider_stock.delete_many({"rider_id": RIDER_ID})
    db.menu_stock_tx.delete_many({"note": {"$regex": "TEST_Rider"}})
    db.users.delete_many({"id": RIDER_ID})


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    tok = r.json().get("account_token")
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": tok, "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


@pytest.fixture(scope="module", autouse=True)
def seed():
    cleanup()
    db.users.insert_one({"id": RIDER_ID, "name": "TEST_Rider Deposit", "username": RIDER_ID, "role": "rider", "active": True, "created_at": "2030-01-01"})
    db.rider_stock.insert_one({"id": uuid.uuid4().hex, "rider_id": RIDER_ID, "date": DATE, "items": {AMERICANO: 10, KOPSU: 5, CREAMY: 4}, "verified_at": "2030-01-15T00:00:00"})
    db.sales.insert_many([
        {"id": uuid.uuid4().hex, "rider_id": RIDER_ID, "date": DATE, "total": 16000, "payment_method": "cash", "payment_parts": [],
         "items": [{"menu_id": AMERICANO, "name": "SI AMERICANO", "qty": 2, "subtotal": 16000}]},
        {"id": uuid.uuid4().hex, "rider_id": RIDER_ID, "date": DATE, "total": 10000, "payment_method": "qris", "payment_parts": [],
         "items": [{"menu_id": KOPSU, "name": "SI KOPSU AREN", "qty": 1, "subtotal": 10000}]},
        {"id": uuid.uuid4().hex, "rider_id": RIDER_ID, "date": DATE, "total": 45000, "payment_method": "split",
         "payment_parts": [{"method": "cash", "amount": 20000}, {"method": "qris", "amount": 25000}],
         "items": [{"menu_id": "bundle-1", "bundle": 1, "name": "BUNDLING 1", "qty": 1, "subtotal": 45000, "components": {AMERICANO: 2, CREAMY: 2}}]},
    ])
    yield
    cleanup()


def forged_payload(remaining=0, wastage=0):
    return {
        "rider_id": RIDER_ID, "date": DATE,
        "total_cash": 99999999, "total_qris": 99999999, "total_cups": 999, "net_cash": 99999999,
        "rows": [{"menu_id": AMERICANO, "remaining": remaining, "wastage": wastage, "cash": 500, "qris": 500, "stock": 9999, "price": 1, "cash_amt": 9e9}],
    }


class TestDepositGate:
    def test_eod_open_rejects_save(self, client):
        r = client.post(f"{BASE_URL}/api/deposits", json=forged_payload())
        assert r.status_code == 400
        assert "EOD" in r.json().get("detail", "")
        assert db.deposits.count_documents({"rider_id": RIDER_ID}) == 0

    def test_eod_summary_server_values(self, client):
        r = client.get(f"{BASE_URL}/api/sales/eod", params={"rider_id": RIDER_ID, "date": DATE})
        assert r.status_code == 200
        d = r.json()
        assert d["closed"] is False
        assert d["total_cash"] == 36000 and d["total_qris"] == 35000 and d["total_cups"] == 7

    def test_close_eod(self, client):
        r = client.post(f"{BASE_URL}/api/sales/eod/close", json={"rider_id": RIDER_ID, "date": DATE})
        assert r.status_code == 200 and r.json()["closed"] is True


class TestDepositServerTotals:
    def test_forged_fields_ignored(self, client):
        r = client.post(f"{BASE_URL}/api/deposits", json=forged_payload(remaining=3, wastage=1))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_cash"] == 36000
        assert d["total_qris"] == 35000
        assert d["total_income"] == 71000
        assert d["total_cups"] == 7
        assert d["net_cash"] == 36000
        assert d["total_wastage"] == 1
        am = next(x for x in d["rows"] if x["menu_id"] == AMERICANO)
        assert am["stock"] == 10 and am["price"] == 8000 and am["total_sold"] == 4
        assert am["cash"] + am["qris"] == 4 and am["cash"] != 500
        assert am["remaining"] == 3 and am["wastage"] == 1
        assert am["diff"] == 2 and am["minus"] == 16000
        assert len(d["bundles"]) == 1 and d["bundles"][0]["amount"] == 45000 and d["bundles"][0]["method"] == "split"

    def test_persisted(self, client):
        r = client.get(f"{BASE_URL}/api/deposits", params={"start": DATE, "end": DATE, "rider_id": RIDER_ID})
        assert r.status_code == 200 and len(r.json()) == 1
        assert r.json()[0]["total_cash"] == 36000 and r.json()[0]["total_qris"] == 35000

    def test_exceeding_stock_rejected(self, client):
        r = client.post(f"{BASE_URL}/api/deposits", json=forged_payload(remaining=6, wastage=1))
        assert r.status_code == 400

    def test_negative_rejected(self, client):
        r = client.post(f"{BASE_URL}/api/deposits", json=forged_payload(remaining=-1, wastage=0))
        assert r.status_code in (400, 422)

    def test_unknown_pic_id_handled(self, client):
        p = forged_payload()
        p["pic_id"] = "does-not-exist"
        r = client.post(f"{BASE_URL}/api/deposits", json=p)
        assert r.status_code in (400, 404), f"got {r.status_code}"

    def test_no_partial_wastage_tx_on_rejected_save(self, client):
        before = db.menu_stock_tx.count_documents({"note": {"$regex": "TEST_Rider"}})
        p = {"rider_id": RIDER_ID, "date": DATE, "rows": [
            {"menu_id": AMERICANO, "remaining": 0, "wastage": 1},
            {"menu_id": CREAMY, "remaining": 5, "wastage": 0},  # creamy available 2 -> must reject
        ]}
        r = client.post(f"{BASE_URL}/api/deposits", json=p)
        assert r.status_code == 400
        after = db.menu_stock_tx.count_documents({"note": {"$regex": "TEST_Rider"}})
        assert after == before, f"wastage tx written despite 400 ({before}->{after})"

    def test_resave_does_not_duplicate_wastage_tx(self, client):
        client.post(f"{BASE_URL}/api/deposits", json=forged_payload(remaining=3, wastage=1))
        before = db.menu_stock_tx.count_documents({"note": {"$regex": "TEST_Rider"}, "date": DATE})
        r = client.post(f"{BASE_URL}/api/deposits", json=forged_payload(remaining=3, wastage=1))
        assert r.status_code == 200
        after = db.menu_stock_tx.count_documents({"note": {"$regex": "TEST_Rider"}, "date": DATE})
        assert after == before, f"re-save duplicated wastage tx ({before}->{after})"
