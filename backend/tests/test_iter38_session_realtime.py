"""Iteration 38: fixed logout policy (WIB midnight / Rider EOD+4h), server session expiry, sync revision."""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

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


def do_login(identifier, pin):
    s = requests.Session()
    for attempt in range(3):
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


def session_doc(s):
    import jwt as pyjwt
    tok = s.cookies.get("si4am_session")
    sid = pyjwt.decode(tok, options={"verify_signature": False})["sid"]
    return mdb.sessions.find_one({"id": sid}), sid


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
    mdb.login_attempts.delete_many({"identifier": {"$in": [f"login:{i}" for i in ids]}})
    mdb.users.delete_many({"id": {"$in": ids}})


# Owner/Admin/Bar Team: next 00:00 WIB
class TestStaffMidnight:
    def test_owner_login_midnight(self):
        s, r = do_login("baa", "130994")
        assert r.status_code == 200
        ends = utc(r.json()["user"].get("session_ends_at") or s.get(f"{API}/auth/me").json()["session_ends_at"])
        assert ends == expected_midnight(), ends
        sess, _ = session_doc(s)
        assert utc(sess["expires_at"]) == expected_midnight()
        c = [c for c in s.cookies if c.name == "si4am_session"][0]
        assert c.secure and c.has_nonstandard_attr("HttpOnly")

    @pytest.mark.parametrize("role", ["admin", "barteam"])
    def test_staff_login_midnight_and_forced_expiry(self, temp_users, role):
        un, pin = USERS[role]
        s, r = do_login(un, pin)
        assert r.status_code == 200, r.text
        print("login user.session_ends_at:", r.json()["user"].get("session_ends_at"))
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert utc(me.json()["session_ends_at"]) == expected_midnight()
        sess, sid = session_doc(s)
        assert utc(sess["expires_at"]) == expected_midnight()
        rev = s.get(f"{API}/sync/revision").json()
        assert utc(rev["session_ends_at"]) == expected_midnight()
        mdb.sessions.update_one({"id": sid}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=5)}})
        assert s.get(f"{API}/auth/me").status_code == 401
        assert mdb.sessions.find_one({"id": sid})["revoked"] is True
        assert s.get(f"{API}/sync/revision").status_code == 401


# Rider: EOD close +4h
class TestRiderEod:
    def test_rider_eod_plus_4h(self, owner, temp_users):
        rid = temp_users["rider"]["id"]
        un, pin = USERS["rider"]
        s1, r1 = do_login(un, pin)
        assert r1.status_code == 200, r1.text
        s2, r2 = do_login(un, pin)
        assert r2.status_code == 200
        before = utc(s1.get(f"{API}/auth/me").json()["session_ends_at"])
        assert before > datetime.now(timezone.utc) + timedelta(days=1)  # pre-EOD long session
        today = datetime.now(WIB).strftime("%Y-%m-%d")
        t0 = datetime.now(timezone.utc)
        r = s1.post(f"{API}/sales/eod/close", json={"rider_id": rid, "date": today})
        assert r.status_code == 200, r.text
        ends = utc(r.json()["session_ends_at"])
        assert abs((ends - (t0 + timedelta(hours=4))).total_seconds()) < 10
        eod = mdb.eod.find_one({"rider_id": rid, "date": today})
        assert utc(eod["closed_at"]) + timedelta(hours=4) == ends
        active = list(mdb.sessions.find({"user_id": rid, "revoked": {"$ne": True}}))
        assert len(active) == 2
        for sess in active:
            assert abs((utc(sess["expires_at"]) - ends).total_seconds()) < 0.01
        for s in (s1, s2):
            me = s.get(f"{API}/auth/me")
            assert me.status_code == 200
            assert abs((utc(me.json()["session_ends_at"]) - ends).total_seconds()) < 0.01
            assert abs((utc(s.get(f"{API}/sync/revision").json()["session_ends_at"]) - ends).total_seconds()) < 0.01
        # force deadline in past
        past = (datetime.now(timezone.utc) - timedelta(hours=4, minutes=1)).isoformat()
        mdb.eod.update_one({"rider_id": rid, "date": today}, {"$set": {"closed_at": past}})
        assert s1.get(f"{API}/auth/me").status_code == 401
        assert s2.get(f"{API}/sync/revision").status_code == 401

    def test_rider_relogin_after_deadline(self, temp_users):
        """Observation: what happens when rider logs in again after deadline passed today."""
        un, pin = USERS["rider"]
        s, r = do_login(un, pin)
        print("relogin after deadline:", r.status_code, r.text[:200])
        me = s.get(f"{API}/auth/me")
        print("me after relogin:", me.status_code)
        # Expected: either login rejected with a clear message, or session usable. 200 login + 401 me = confusing
        assert not (r.status_code == 200 and me.status_code == 401), "Login succeeds but session is immediately expired"


# Revision endpoint
class TestRevision:
    def test_revision_increments_on_mutation(self, owner, temp_users):
        r0 = owner.get(f"{API}/sync/revision")
        assert r0.status_code == 200
        rev0 = r0.json()["revision"]
        assert isinstance(rev0, int)
        assert "session_ends_at" in r0.json()
        # auth POST does not increment
        owner.post(f"{API}/auth/verify-pin", json={"pin": "130994"})
        assert owner.get(f"{API}/sync/revision").json()["revision"] == rev0
        # failed mutation does not increment
        bad = owner.post(f"{API}/users", json={"name": "x", "username": "baa", "role": "admin", "pin": "123456"})
        assert bad.status_code >= 400
        assert owner.get(f"{API}/sync/revision").json()["revision"] == rev0
        # successful PUT increments
        uid_ = temp_users["barteam"]["id"]
        up = owner.put(f"{API}/users/{uid_}", json={"name": "TEST barteam upd"})
        print("PUT user:", up.status_code, up.text[:150])
        assert up.status_code == 200
        assert owner.get(f"{API}/sync/revision").json()["revision"] == rev0 + 1

    def test_revision_unauthenticated(self):
        assert requests.get(f"{API}/sync/revision").status_code == 401


# Auth regressions
class TestAuthRegression:
    def test_logout_revokes(self, temp_users):
        un, pin = USERS["admin"]
        s, r = do_login(un, pin)
        assert r.status_code == 200
        assert s.post(f"{API}/auth/logout").status_code == 200
        assert s.get(f"{API}/auth/me").status_code == 401

    def test_bcrypt_format(self, temp_users):
        u = mdb.users.find_one({"username": USERS["admin"][0]})
        assert u["pin_hash"].startswith("$2b$")

    def test_bruteforce_lockout(self, temp_users):
        un, pin = USERS["barteam"]
        time.sleep(61)
        s = requests.Session()
        tok = s.post(f"{API}/auth/identify", json={"identifier": un, "terms_accepted": True, "privacy_accepted": True}).json()["account_token"]
        codes = [s.post(f"{API}/auth/login", json={"account_token": tok, "pin": "000000"}).status_code for _ in range(5)]
        assert codes == [401] * 5
        r = s.post(f"{API}/auth/login", json={"account_token": tok, "pin": pin})
        assert r.status_code == 429


# Identify must not resolve unknown identifiers to users with empty whatsapp (fixed by T1 in iter38)
class TestIdentifyResolution:
    def test_unknown_identifier_rejected(self, temp_users):
        r = requests.post(f"{API}/auth/identify", json={"identifier": f"nope_{SUFFIX}", "terms_accepted": True, "privacy_accepted": True})
        assert r.status_code == 401

    @pytest.mark.parametrize("role", ["admin", "barteam", "rider"])
    def test_identify_returns_exact_user(self, temp_users, role):
        r = requests.post(f"{API}/auth/identify", json={"identifier": USERS[role][0], "terms_accepted": True, "privacy_accepted": True})
        assert r.status_code == 200
        assert r.json()["user"]["username"] == USERS[role][0]
