# Iteration 35: Auth identify payload used by RiderGuide (role + id), Owner login/logout regression, temp Rider lifecycle.
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
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
RIDER = (f"test_r35_{uuid.uuid4().hex[:6]}", "357913")
STATE = {}


def identify(s, ident):
    return s.post(f"{API}/auth/identify", json={"identifier": ident, "terms_accepted": True, "privacy_accepted": True})


def cleanup():
    ids = [u["id"] for u in db.users.find({"username": {"$regex": "^test_r35_"}}, {"id": 1})]
    for c in ("sessions", "audit_logs", "files", "login_attempts"):
        db[c].delete_many({"user_id": {"$in": ids}})
    db.users.delete_many({"id": {"$in": ids}})


@pytest.fixture(scope="module", autouse=True)
def module_data():
    cleanup()
    yield
    cleanup()


@pytest.fixture(scope="module")
def owner():
    s = requests.Session()
    r = identify(s, "baa")
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    return s


class TestIter35:
    def test_owner_login_cookie(self, owner):
        assert "si4am_session" in owner.cookies.get_dict()
        r = owner.get(f"{API}/auth/me")
        assert r.status_code == 200
        body = r.json()
        u = body.get("user", body)
        assert u["role"] == "owner"

    def test_owner_identify_role_owner(self):
        r = identify(requests.Session(), "baa")
        assert r.json()["user"]["role"] == "owner"

    def test_create_rider_identify_has_role_and_id(self, owner):
        r = owner.post(f"{API}/users", json={"name": "TEST Rider35", "username": RIDER[0], "pin": RIDER[1], "role": "rider", "active": True})
        assert r.status_code == 200, r.text
        STATE["rid"] = r.json()["id"]
        r = identify(requests.Session(), RIDER[0])
        assert r.status_code == 200
        u = r.json()["user"]
        assert u["role"] == "rider" and u["id"] == STATE["rid"]
        assert "pin_hash" not in u and "_id" not in u

    def test_rider_login(self):
        s = requests.Session()
        tok = identify(s, RIDER[0]).json()["account_token"]
        r = s.post(f"{API}/auth/login", json={"account_token": tok, "pin": RIDER[1], "remember": True})
        assert r.status_code == 200, r.text
        assert r.json()["user"]["role"] == "rider"

    def test_wrong_pin_rejected(self):
        s = requests.Session()
        tok = identify(s, RIDER[0]).json()["account_token"]
        r = s.post(f"{API}/auth/login", json={"account_token": tok, "pin": "000000", "remember": True})
        assert r.status_code in (400, 401)

    def test_owner_logout(self):
        s = requests.Session()
        tok = identify(s, "baa").json()["account_token"]
        assert s.post(f"{API}/auth/login", json={"account_token": tok, "pin": "130994", "remember": True}).status_code == 200
        assert s.post(f"{API}/auth/logout").status_code == 200
        assert s.get(f"{API}/auth/me").status_code == 401
