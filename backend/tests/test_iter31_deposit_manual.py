# Iteration 31: Setoran/Deposit manual stock/cash/qris/remaining/wastage contract + hardening; Invoice calc.
# Run sequentially: pytest tests/test_iter31_deposit_manual.py -n 0
# Seeds a TEST_ temporary rider + stock + sales directly in Mongo and hard-deletes everything at teardown.
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
PREV_DATE = "2030-01-14"
AMERICANO = "6cc0ca7c-b6f4-4b0c-b6e6-c21707d4e4e4"  # 8000
KOPSU = "c9750dec-4968-4cd2-be2b-0695eb0bafe7"  # 10000
CREAMY = "6c5553d9-8c31-4a73-8348-c3e4b1c819f5"  # 12000
RIDER_ID = "TEST_rider_" + uuid.uuid4().hex[:8]
NONRIDER_ID = "TEST_bar_" + uuid.uuid4().hex[:8]


def cleanup():
    ids = [RIDER_ID, NONRIDER_ID]
    dep_ids = [d["id"] for d in db.deposits.find({"rider_id": {"$in": ids}})]
    inv_ids = [i["id"] for i in db.invoices.find({"customer_name": {"$regex": "^TEST_"}})]
    db.notifications.delete_many({"ref_id": {"$in": dep_ids + inv_ids}})
    db.deposits.delete_many({"rider_id": {"$in": ids}})
    db.sales.delete_many({"rider_id": {"$in": ids}})
    db.eod.delete_many({"rider_id": {"$in": ids}})
    db.rider_stock.delete_many({"rider_id": {"$in": ids}})
    db.menu_stock_tx.delete_many({"rider_id": {"$in": ids}})
    db.sessions.delete_many({"user_id": {"$in": ids}})
    db.users.delete_many({"id": {"$in": ids}})
    db.invoices.delete_many({"customer_name": {"$regex": "^TEST_"}})
    db.customers.delete_many({"name": {"$regex": "^TEST_"}})


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": r.json()["account_token"], "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    s.me = r.json()["user"]
    return s


@pytest.fixture(scope="module", autouse=True)
def seed():
    cleanup()
    db.users.insert_one({"id": RIDER_ID, "name": "TEST_Rider Deposit", "username": RIDER_ID, "role": "rider", "active": True, "created_at": "2030-01-01"})
    db.users.insert_one({"id": NONRIDER_ID, "name": "TEST_Bar", "username": NONRIDER_ID, "role": "bar", "active": True, "created_at": "2030-01-01"})
    db.rider_stock.insert_one({"id": uuid.uuid4().hex, "rider_id": RIDER_ID, "date": DATE, "items": {AMERICANO: 10, KOPSU: 5, CREAMY: 4}, "verified_at": "2030-01-15T00:00:00"})
    db.sales.insert_one({"id": uuid.uuid4().hex, "rider_id": RIDER_ID, "date": DATE, "total": 16000, "payment_method": "cash", "payment_parts": [],
                         "items": [{"menu_id": AMERICANO, "name": "SI AMERICANO", "qty": 2, "subtotal": 16000}]})
    # EOD for non-rider so role gate is the only thing rejecting it
    db.eod.insert_one({"rider_id": NONRIDER_ID, "date": DATE, "closed_by": "TEST", "time": "20:00"})
    yield
    cleanup()


def manual_payload(**over):
    rows = [
        {"menu_id": AMERICANO, "stock": 12, "cash": 3, "qris": 2, "remaining": 4, "wastage": 1},  # diff 2 -> minus 16000
        {"menu_id": KOPSU, "stock": 6, "cash": 1, "qris": 4, "remaining": 1, "wastage": 0},  # diff 0
        {"menu_id": CREAMY, "stock": 3, "cash": 0, "qris": 1, "remaining": 0, "wastage": 2},  # diff 0
    ]
    p = {"rider_id": RIDER_ID, "date": DATE, "rows": rows}
    p.update(over)
    return p


class TestGate:
    def test_before_eod_closed_is_400(self, client):
        r = client.post(f"{BASE_URL}/api/deposits", json=manual_payload())
        assert r.status_code == 400 and "EOD" in r.json().get("detail", "")
        assert db.deposits.count_documents({"rider_id": RIDER_ID}) == 0
        assert db.menu_stock_tx.count_documents({"rider_id": RIDER_ID}) == 0

    def test_close_eod(self, client):
        r = client.post(f"{BASE_URL}/api/sales/eod/close", json={"rider_id": RIDER_ID, "date": DATE})
        assert r.status_code == 200 and r.json()["closed"] is True


class TestManualDeposit:
    def test_manual_values_persist_and_totals(self, client):
        r = client.post(f"{BASE_URL}/api/deposits", json=manual_payload())
        assert r.status_code == 200, r.text
        d = r.json()
        am = next(x for x in d["rows"] if x["menu_id"] == AMERICANO)
        assert (am["stock"], am["cash"], am["qris"], am["remaining"], am["wastage"]) == (12, 3, 2, 4, 1)
        assert am["total_sold"] == 5 and am["diff"] == 2 and am["minus"] == 16000
        # cash = 3*8000 + 1*10000 + 0 = 34000 ; qris = 2*8000 + 4*10000 + 1*12000 = 68000
        assert d["total_cash"] == 34000
        assert d["total_qris"] == 68000
        assert d["total_income"] == 102000
        assert d["total_cups"] == 11
        assert d["total_wastage"] == 3
        assert d["minus"] == 16000 and d["new_debt"] == 16000
        assert d["initial_debt"] == 0 and d["remaining_debt"] == 16000
        assert d["net_cash"] == 34000
        assert d["pic_id"] == client.me["id"]

    def test_persisted_via_get(self, client):
        r = client.get(f"{BASE_URL}/api/deposits", params={"start": DATE, "end": DATE, "rider_id": RIDER_ID})
        assert r.status_code == 200 and len(r.json()) == 1
        d = r.json()[0]
        assert d["total_cash"] == 34000 and d["total_qris"] == 68000
        kop = next(x for x in d["rows"] if x["menu_id"] == KOPSU)
        assert (kop["stock"], kop["cash"], kop["qris"], kop["remaining"]) == (6, 1, 4, 1)

    def test_wastage_tx_written(self, client):
        tx = list(db.menu_stock_tx.find({"rider_id": RIDER_ID, "source": "deposit", "type": "wastage"}))
        assert sorted((t["menu_id"], t["qty"]) for t in tx) == sorted([(AMERICANO, 1), (CREAMY, 2)])

    def test_resave_no_duplicate_wastage_and_upsert(self, client):
        r = client.post(f"{BASE_URL}/api/deposits", json=manual_payload())
        assert r.status_code == 200
        assert db.menu_stock_tx.count_documents({"rider_id": RIDER_ID, "source": "deposit"}) == 2
        assert db.deposits.count_documents({"rider_id": RIDER_ID, "date": DATE}) == 1

    def test_resave_changed_wastage_replaces(self, client):
        p = manual_payload()
        p["rows"][2]["wastage"] = 0
        r = client.post(f"{BASE_URL}/api/deposits", json=p)
        assert r.status_code == 200 and r.json()["total_wastage"] == 1
        assert db.menu_stock_tx.count_documents({"rider_id": RIDER_ID, "source": "deposit"}) == 1

    def test_unknown_pic_does_not_500(self, client):
        r = client.post(f"{BASE_URL}/api/deposits", json=manual_payload(pic_id="does-not-exist"))
        assert r.status_code in (200, 400, 404), r.status_code
        if r.status_code == 200:
            assert r.json()["pic_id"] == client.me["id"]

    def test_non_rider_rejected(self, client):
        r = client.post(f"{BASE_URL}/api/deposits", json=manual_payload(rider_id=NONRIDER_ID))
        assert r.status_code in (400, 404)
        assert db.deposits.count_documents({"rider_id": NONRIDER_ID}) == 0

    def test_invalid_later_row_no_partial_writes(self, client):
        before_tx = db.menu_stock_tx.count_documents({"rider_id": RIDER_ID})
        before_dep = db.deposits.find_one({"rider_id": RIDER_ID, "date": DATE}, {"_id": 0, "updated_at": 1, "total_cash": 1})
        p = manual_payload()
        p["rows"][0]["wastage"] = 5
        p["rows"][2]["remaining"] = -1  # invalid later row
        r = client.post(f"{BASE_URL}/api/deposits", json=p)
        assert r.status_code in (400, 422)
        assert db.menu_stock_tx.count_documents({"rider_id": RIDER_ID}) == before_tx
        after_dep = db.deposits.find_one({"rider_id": RIDER_ID, "date": DATE}, {"_id": 0, "updated_at": 1, "total_cash": 1})
        assert after_dep == before_dep

    def test_overcount_row_behaviour(self, client):
        # sold+remaining+wastage > stock : record what backend does (informational)
        p = manual_payload()
        p["rows"][0] = {"menu_id": AMERICANO, "stock": 2, "cash": 3, "qris": 2, "remaining": 4, "wastage": 1}
        r = client.post(f"{BASE_URL}/api/deposits", json=p)
        print("OVERCOUNT status", r.status_code, r.text[:200])
        assert r.status_code in (200, 400)
        # restore
        client.post(f"{BASE_URL}/api/deposits", json=manual_payload())

    def test_notification_count_on_resave(self, client):
        dep = db.deposits.find_one({"rider_id": RIDER_ID, "date": DATE})
        n = db.notifications.count_documents({"ref_id": dep["id"]})
        print("NOTIFICATIONS for one deposit after multiple resaves:", n)


class TestInvoice:
    def test_invoice_calc(self, client):
        body = {"customer_name": "TEST_Customer", "customer_phone": "081200000000", "date": DATE, "payment_method": "cash",
                "rows": [{"menu_id": AMERICANO, "qty": 3}, {"menu_id": CREAMY, "qty": 2}, {"menu_id": KOPSU, "qty": 0}],
                "discount": 4000, "down_payment": 20000, "note": ""}
        r = client.post(f"{BASE_URL}/api/invoices", json=body)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["subtotal"] == 48000 and d["total"] == 44000 and d["remaining"] == 24000 and d["status"] == "unpaid"
        assert d["cups"] == 5 and len(d["rows"]) == 2
        g = client.get(f"{BASE_URL}/api/invoices").json()
        assert any(i["id"] == d["id"] and i["total"] == 44000 for i in g)
