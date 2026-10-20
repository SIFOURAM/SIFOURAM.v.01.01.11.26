# Iteration 10: Owner-only auth (identify -> PIN), owner endpoints, post-reset state, rank tiers
import os
import sys
import asyncio
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
OWNER = {"identifier": "baa", "pin": "130994"}


def identify(ident, terms=True, privacy=True):
    return requests.post(f"{BASE_URL}/api/auth/identify",
                         json={"identifier": ident, "terms_accepted": terms, "privacy_accepted": privacy}, timeout=20)


@pytest.fixture(scope="module")
def account_token():
    r = identify(OWNER["identifier"])
    assert r.status_code == 200, r.text
    return r.json()["account_token"]


@pytest.fixture(scope="module")
def token(account_token):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"account_token": account_token, "pin": OWNER["pin"], "remember": True}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def H(token):
    return {"Authorization": f"Bearer {token}"}


# ---- Auth ----
class TestAuth:
    def test_identify_owner(self):
        r = identify("baa")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["account_token"], str) and d["user"]["role"] == "owner"
        assert "pin_hash" not in d["user"] and "password_hash" not in d["user"]

    def test_identify_by_email(self):
        r = identify("baazulfikar@gmail.com")
        assert r.status_code == 200

    def test_identify_unknown(self):
        r = identify("TEST_nobody_xyz")
        assert r.status_code == 404
        assert "tidak ditemukan" in r.json()["detail"]

    def test_identify_without_consent(self):
        r = identify("baa", terms=False, privacy=True)
        assert r.status_code == 400
        r = identify("baa", terms=True, privacy=False)
        assert r.status_code == 400

    def test_identify_token_cannot_auth_me(self, account_token):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {account_token}"}, timeout=20)
        assert r.status_code == 401

    def test_wrong_pin(self):
        at = identify("baa").json()["account_token"]
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"account_token": at, "pin": "000000"}, timeout=20)
        assert r.status_code == 401
        # reset attempt counter with a correct login
        r2 = requests.post(f"{BASE_URL}/api/auth/login", json={"account_token": at, "pin": OWNER["pin"]}, timeout=20)
        assert r2.status_code == 200

    def test_access_token_rejected_as_account_token(self, token):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"account_token": token, "pin": OWNER["pin"]}, timeout=20)
        assert r.status_code == 401

    def test_garbage_account_token(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"account_token": "abc", "pin": OWNER["pin"]}, timeout=20)
        assert r.status_code == 401

    def test_me(self, H):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=H, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "owner" and d["username"] == "baa"
        assert "pin_hash" not in d

    def test_no_token(self):
        assert requests.get(f"{BASE_URL}/api/auth/me", timeout=20).status_code == 401
        assert requests.get(f"{BASE_URL}/api/reports/sales?start=2026-01-01&end=2026-01-31", timeout=20).status_code == 401


# ---- Owner endpoints ----
class TestOwnerEndpoints:
    def test_users_only_owner(self, H):
        r = requests.get(f"{BASE_URL}/api/users", headers=H, timeout=20)
        assert r.status_code == 200
        users = r.json()
        assert len(users) == 1 and users[0]["username"] == "baa" and users[0]["role"] == "owner"
        roles = {u["role"] for u in users}
        assert roles <= {"owner", "admin", "barteam", "rider"}

    def test_create_user_invalid_role_and_pin(self, H):
        r = requests.post(f"{BASE_URL}/api/users", headers=H, json={"name": "TEST_x", "username": "TEST_x_inv", "role": "superadmin", "pin": "123456"}, timeout=20)
        assert r.status_code == 400
        r = requests.post(f"{BASE_URL}/api/users", headers=H, json={"name": "TEST_x", "username": "TEST_x_inv", "role": "rider", "pin": "12ab"}, timeout=20)
        assert r.status_code == 400

    def test_owner_cannot_demote_self(self, H):
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=H, timeout=20).json()
        r = requests.put(f"{BASE_URL}/api/users/{me['id']}", headers=H, json={"role": "rider"}, timeout=20)
        assert r.status_code == 400

    def test_rider_rank_requires_rider(self, H):
        r = requests.get(f"{BASE_URL}/api/rider-rank?start=2026-01-01&end=2026-01-31", headers=H, timeout=20)
        assert r.status_code == 400

    def test_rider_rank_unknown_rider_zero(self, H):
        r = requests.get(f"{BASE_URL}/api/rider-rank?start=2026-01-01&end=2026-01-31&rider_id=TEST_none", headers=H, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["gross"] == 0 and d["rank"]["name"] == "Herald"

    def test_reports_zero(self, H):
        r = requests.get(f"{BASE_URL}/api/reports/sales?start=2020-01-01&end=2030-12-31&payment_method=all&order_type=all", headers=H, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["transactions"] == 0 and d["revenue"] == 0 and d["average_order"] == 0
        assert d["products"] == [] and d["daily_revenue"] == [] and d["hourly"] == []

    def test_gps_owner_forbidden(self, H):
        r = requests.post(f"{BASE_URL}/api/gps", headers=H, json={"lat": -6.2, "lng": 106.8}, timeout=20)
        assert r.status_code == 403


# ---- Reset state (DB) ----
class TestResetState:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)

    def test_collections_empty_and_stock_zero(self):
        from motor.motor_asyncio import AsyncIOMotorClient

        async def chk():
            db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
            out = {}
            for c in ["coach_chats", "expenses", "handovers", "withdrawals", "inventory_tx", "menu_stock_tx", "rider_stock", "sales", "deposits", "invoices"]:
                out[c] = await db[c].count_documents({})
            out["materials"] = await db.materials.count_documents({})
            out["menus"] = await db.menus.count_documents({})
            out["mat_nonzero"] = await db.materials.count_documents({"stock": {"$ne": 0}})
            out["menu_nonzero"] = await db.menus.count_documents({"stock": {"$ne": 0}})
            return out
        o = asyncio.run(chk())
        for c in ["coach_chats", "expenses", "handovers", "withdrawals", "inventory_tx", "menu_stock_tx", "rider_stock"]:
            assert o[c] == 0, f"{c} not empty: {o[c]}"
        assert o["materials"] > 0 and o["menus"] > 0
        assert o["mat_nonzero"] == 0 and o["menu_nonzero"] == 0

    def test_api_materials_menus_zero(self, H):
        mats = requests.get(f"{BASE_URL}/api/materials", headers=H, timeout=20).json()
        menus = requests.get(f"{BASE_URL}/api/menus", headers=H, timeout=20).json()
        assert len(mats) > 0 and all(m["stock"] == 0 for m in mats)
        assert len(menus) > 0 and all(m["stock"] == 0 for m in menus)


# ---- Rank tiers (unit) ----
class TestRankTiers:
    def test_boundaries(self):
        sys.path.insert(0, "/app/backend")
        import server
        f = server.rider_rank_for
        assert f(0)["name"] == "Herald"
        assert f(1749999)["name"] == "Herald"
        assert f(1750000)["name"] == "Warriors"
        assert f(2520000)["name"] == "Masters"
        assert f(3220000)["name"] == "Divine"
        assert f(3999999)["name"] == "Divine"
        assert f(4000000)["name"] == "Immortal"
