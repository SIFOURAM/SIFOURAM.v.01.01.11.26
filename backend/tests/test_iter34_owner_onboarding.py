# Iteration 34: Owner onboarding checklist GET /api/onboarding/owner
# (no rider -> show=false; rider -> show=true; stock -> pending verify; rider verifies -> hidden; RBAC 403).
# Run: pytest tests/test_iter34_owner_onboarding.py -n 0 -p no:cacheprovider
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
SUFFIX = uuid.uuid4().hex[:6]
TODAY = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
USERS = {
    "rider": (f"test_r34_{SUFFIX}", "246810"),
    "rider2": (f"test_q34_{SUFFIX}", "246812"),
    "admin": (f"test_a34_{SUFFIX}", "246811"),
    "barteam": (f"test_b34_{SUFFIX}", "246813"),
}
STATE = {}
MENUS = [m["id"] for m in db.menus.find({}, {"_id": 0, "id": 1}).sort("order", 1).limit(2)]
MENU_BASELINE = {m["id"]: m.get("stock", 0) for m in db.menus.find({}, {"_id": 0, "id": 1, "stock": 1})}


def login(identifier, pin):
    s = requests.Session()
    r = s.post(f"{API}/auth/identify", json={"identifier": identifier, "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": pin, "remember": True})
    assert r.status_code == 200, r.text
    return s


def cleanup():
    ids = [u["id"] for u in db.users.find({"username": {"$regex": "^test_[rqab]34_"}}, {"id": 1})]
    for c in ("rider_stock", "menu_stock_tx", "sales", "eod", "attendance"):
        db[c].delete_many({"rider_id": {"$in": ids}})
    db.files.delete_many({"user_id": {"$in": ids}})
    db.sessions.delete_many({"user_id": {"$in": ids}})
    db.audit_logs.delete_many({"user_id": {"$in": ids}})
    db.users.delete_many({"id": {"$in": ids}})
    for mid, stock in MENU_BASELINE.items():
        db.menus.update_one({"id": mid}, {"$set": {"stock": stock}})


@pytest.fixture(scope="module", autouse=True)
def module_data():
    cleanup()
    yield
    cleanup()


@pytest.fixture(scope="module")
def owner():
    return login("baa", "130994")


class TestOwnerOnboarding:
    def test_01_no_riders_show_false(self, owner):
        assert db.users.count_documents({"role": "rider", "active": {"$ne": False}}) == 0
        r = owner.get(f"{API}/onboarding/owner")
        assert r.status_code == 200, r.text
        assert r.json() == {"show": False, "rider": None, "stock": None, "verified": False}

    def test_02_create_rider_show_true(self, owner):
        name, pin = USERS["rider"]
        r = owner.post(f"{API}/users", json={"name": "TEST Rider34", "username": name, "pin": pin, "role": "rider", "active": True})
        assert r.status_code == 200, r.text
        STATE["rider_id"] = r.json()["id"]
        d = owner.get(f"{API}/onboarding/owner").json()
        assert d["show"] is True and d["verified"] is False and d["stock"] is None
        assert d["rider"]["id"] == STATE["rider_id"] and d["rider"]["name"] == "TEST Rider34"
        assert "_id" not in d["rider"]

    def test_03_second_rider_keeps_first(self, owner):
        name, pin = USERS["rider2"]
        r = owner.post(f"{API}/users", json={"name": "TEST Rider34b", "username": name, "pin": pin, "role": "rider", "active": True})
        assert r.status_code == 200, r.text
        STATE["rider2_id"] = r.json()["id"]
        d = owner.get(f"{API}/onboarding/owner").json()
        assert d["rider"]["id"] == STATE["rider_id"]

    def test_04_allocate_stock_pending_verify(self, owner):
        for mid in MENUS:
            db.menus.update_one({"id": mid}, {"$set": {"stock": 20}})
        r = owner.post(f"{API}/rider-stock", json={"rider_id": STATE["rider_id"], "date": TODAY, "items": {MENUS[0]: 5, MENUS[1]: 3}, "photo": PHOTO})
        assert r.status_code == 200, r.text
        STATE["stock_id"] = r.json()["id"]
        d = owner.get(f"{API}/onboarding/owner").json()
        assert d["show"] is True and d["verified"] is False
        assert d["stock"] == {"id": STATE["stock_id"], "total": 8}

    def test_05_rbac_403(self, owner):
        for role in ("admin", "barteam"):
            name, pin = USERS[role]
            r = owner.post(f"{API}/users", json={"name": f"TEST {role}34", "username": name, "pin": pin, "role": role, "active": True})
            assert r.status_code == 200, r.text
            s = login(name, pin)
            assert s.get(f"{API}/onboarding/owner").status_code == 403
        rs = login(*USERS["rider"])
        STATE["rider_session"] = rs
        assert rs.get(f"{API}/onboarding/owner").status_code == 403
        assert requests.get(f"{API}/onboarding/owner").status_code == 401

    def test_06_rider_verify_hides_card(self, owner):
        rs = STATE["rider_session"]
        # sale blocked before verification? check pos/stock reachable
        r = rs.post(f"{API}/rider-stock/{STATE['stock_id']}/verify", json={"photo": PHOTO})
        assert r.status_code == 200, r.text
        assert r.json()["verified_at"]
        d = owner.get(f"{API}/onboarding/owner").json()
        assert d == {"show": False, "rider": None, "stock": None, "verified": True}

    def test_07_rider_pos_stock(self):
        rs = STATE["rider_session"]
        r = rs.get(f"{API}/pos/stock", params={"rider_id": STATE["rider_id"], "date": TODAY})
        assert r.status_code == 200, r.text
        print("POS stock:", r.json())

    def test_08_completed_onboarding_stays_hidden(self, owner):
        db.users.update_one({"id": STATE["rider_id"]}, {"$set": {"active": False}})
        d = owner.get(f"{API}/onboarding/owner").json()
        db.users.update_one({"id": STATE["rider_id"]}, {"$set": {"active": True}})
        assert d == {"show": False, "rider": None, "stock": None, "verified": True}
