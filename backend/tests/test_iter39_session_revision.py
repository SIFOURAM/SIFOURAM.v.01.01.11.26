"""Iteration 39: fixed logout policies, Rider EOD+4h login rejection, Mongo-persisted app_revision."""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for ln in f:
            if ln.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = ln.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

_env = {}
with open("/app/backend/.env") as f:
    for ln in f:
        if "=" in ln:
            k, v = ln.strip().split("=", 1)
            _env[k] = v.strip('"')
mdb = MongoClient(_env["MONGO_URL"])[_env["DB_NAME"]]

WIB = timezone(timedelta(hours=7))
SUFFIX = uuid.uuid4().hex[:6]
USERS = {
    "admin": (f"test_adm_{SUFFIX}", "271828"),
    "barteam": (f"test_bar_{SUFFIX}", "314159"),
    "rider": (f"test_rid_{SUFFIX}", "161803"),
}


def utc(v):
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)
    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)


def expected_midnight():
    now = datetime.now(WIB)
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def today():
    return datetime.now(WIB).strftime("%Y-%m-%d")


def do_login(identifier, pin):
    s = requests.Session()
    for _ in range(3):
        r = s.post(f"{API}/auth/identify", json={"identifier": identifier, "terms_accepted": True, "privacy_accepted": True})
        if r.status_code == 429:
            time.sleep(61)
            continue
        assert r.status_code == 200, r.text
        r2 = s.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": pin, "remember": True})
        if r2.status_code == 429:
            time.sleep(61)
            continue
        return s, r2
    pytest.fail("rate limited")


def sid_of(s):
    return pyjwt.decode(s.cookies.get("si4am_session"), options={"verify_signature": False})["sid"]


def db_rev():
    c = mdb.counters.find_one({"key": "app_revision"})
    return c.get("value", 0) if c else 0


@pytest.fixture(scope="module")
def owner():
    s, r = do_login("baa", "130994")
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def temp_users(owner):
    out = {}
    for role, (un, pin) in USERS.items():
        r = owner.post(f"{API}/users", json={"name": f"TEST {role}", "username": un, "role": role, "pin": pin})
        assert r.status_code == 200, r.text
        out[role] = r.json()
    yield out
    ids = [u["id"] for u in out.values()]
    mdb.sessions.delete_many({"user_id": {"$in": ids}})
    mdb.eod.delete_many({"rider_id": {"$in": ids}})
    mdb.attendance.delete_many({"rider_id": {"$in": ids}})
    mdb.gps.delete_many({"rider_id": {"$in": ids}})
    mdb.login_attempts.delete_many({"identifier": {"$in": [f"login:{i}" for i in ids]}})
    mdb.users.delete_many({"id": {"$in": ids}})


# Owner/Admin/Bar Team: login response, session doc, /auth/me, /sync/revision all equal next 00:00 WIB
class TestStaffMidnight:
    def test_owner_login_response_midnight(self):
        s, r = do_login("baa", "130994")
        assert r.status_code == 200
        ends = utc(r.json()["user"]["session_ends_at"])
        assert ends == expected_midnight()
        assert ends.astimezone(WIB).hour == 0 and ends.astimezone(WIB).minute == 0
        assert utc(mdb.sessions.find_one({"id": sid_of(s)})["expires_at"]) == expected_midnight()
        cookie = [c for c in s.cookies if c.name == "si4am_session"][0]
        assert cookie.secure and cookie.has_nonstandard_attr("HttpOnly")
        assert abs(cookie.expires - expected_midnight().timestamp()) < 120

    @pytest.mark.parametrize("role", ["admin", "barteam"])
    def test_staff_midnight(self, temp_users, role):
        s, r = do_login(*USERS[role])
        assert r.status_code == 200, r.text
        assert utc(r.json()["user"]["session_ends_at"]) == expected_midnight()
        assert utc(s.get(f"{API}/auth/me").json()["session_ends_at"]) == expected_midnight()
        assert utc(s.get(f"{API}/sync/revision").json()["session_ends_at"]) == expected_midnight()
        mdb.sessions.update_one({"id": sid_of(s)}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=2)}})
        assert s.get(f"{API}/auth/me").status_code == 401


# Rider: EOD + 4h, re-close keeps first closed_at, login after deadline rejected
class TestRiderEod:
    def test_rider_pre_eod_session(self, temp_users):
        s, r = do_login(*USERS["rider"])
        assert r.status_code == 200
        assert utc(r.json()["user"]["session_ends_at"]) > datetime.now(timezone.utc) + timedelta(days=1)

    def test_rider_eod_4h_and_reclose(self, temp_users):
        rid = temp_users["rider"]["id"]
        s, r = do_login(*USERS["rider"])
        assert r.status_code == 200
        t0 = datetime.now(timezone.utc)
        c1 = s.post(f"{API}/sales/eod/close", json={"rider_id": rid, "date": today()})
        assert c1.status_code == 200, c1.text
        ends = utc(c1.json()["session_ends_at"])
        assert abs((ends - (t0 + timedelta(hours=4))).total_seconds()) < 10
        assert not abs((ends - (t0 + timedelta(hours=3))).total_seconds()) < 60
        assert abs((utc(s.get(f"{API}/auth/me").json()["session_ends_at"]) - ends).total_seconds()) < 0.01
        # new login after EOD still allowed (within 4h) and returns same deadline
        s2, r2 = do_login(*USERS["rider"])
        assert r2.status_code == 200
        assert abs((utc(r2.json()["user"]["session_ends_at"]) - ends).total_seconds()) < 0.01
        time.sleep(2)
        c2 = s.post(f"{API}/sales/eod/close", json={"rider_id": rid, "date": today()})
        assert c2.status_code == 200
        assert abs((utc(c2.json()["session_ends_at"]) - ends).total_seconds()) < 0.01, "re-close extended deadline"

    def test_rider_login_after_deadline_rejected(self, temp_users):
        rid = temp_users["rider"]["id"]
        s_old, _ = do_login(*USERS["rider"])
        past = (datetime.now(timezone.utc) - timedelta(hours=4, minutes=1)).isoformat()
        mdb.eod.update_one({"rider_id": rid, "date": today()}, {"$set": {"closed_at": past}})
        assert s_old.get(f"{API}/auth/me").status_code == 401
        s, r = do_login(*USERS["rider"])
        assert r.status_code == 403, r.text
        assert "empat jam" in r.json()["detail"]
        assert s.cookies.get("si4am_session") is None


# app_revision persisted in Mongo; normal mutations increment, GPS / notification-read / auth / failures don't
class TestRevision:
    def test_revision_matches_mongo(self, owner):
        api_rev = owner.get(f"{API}/sync/revision").json()["revision"]
        assert api_rev == db_rev()

    def test_mutation_increments(self, owner):
        r0 = owner.get(f"{API}/sync/revision").json()["revision"]
        menu = mdb.menus.find_one({"active": {"$ne": False}})
        p = owner.post(f"{API}/menu-stock/produce", json={"menu_id": menu["id"], "qty": 3, "date": today(), "type": "adjust", "note": "TEST"})
        assert p.status_code == 200, p.text
        assert owner.get(f"{API}/sync/revision").json()["revision"] == r0 + 1
        assert db_rev() == r0 + 1
        owner.post(f"{API}/menu-stock/produce", json={"menu_id": menu["id"], "qty": 0, "date": today(), "type": "adjust", "note": "TEST reset"})

    def test_notification_read_no_increment(self, owner):
        r0 = db_rev()
        assert owner.post(f"{API}/notifications/read").status_code == 200
        assert db_rev() == r0

    def test_gps_no_increment(self, temp_users):
        rid = temp_users["rider"]["id"]
        mdb.eod.delete_many({"rider_id": rid})
        mdb.attendance.insert_one({"id": f"TEST_att_{SUFFIX}", "rider_id": rid, "date": today(), "checkout_at": None})
        s, r = do_login(*USERS["rider"])
        assert r.status_code == 200, r.text
        r0 = db_rev()
        g = s.post(f"{API}/gps", json={"lat": -6.2, "lng": 106.8})
        assert g.status_code == 200, g.text
        assert db_rev() == r0

    def test_auth_and_failed_no_increment(self, owner):
        r0 = db_rev()
        owner.post(f"{API}/auth/verify-pin", json={"pin": "130994"})
        owner.post(f"{API}/users", json={"name": "x", "username": "baa", "role": "admin", "pin": "123456"})
        assert db_rev() == r0
