# Iteration 12: Rider stock authorization regression (Owner only, non-persistent)
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    acct = r.json().get("account_token")
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"account_token": acct, "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "owner"
    return r.json()["token"]


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}"}


# Owner can read rider stock history
def test_owner_history(h):
    r = requests.get(f"{BASE_URL}/api/rider-stock/history", params={"start": "2000-01-01", "end": "2100-01-01"}, headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_owner_get_rider_stock_nonexistent(h):
    r = requests.get(f"{BASE_URL}/api/rider-stock", params={"rider_id": "nonexistent", "date": "2026-01-01"}, headers=h)
    assert r.status_code == 200
    assert r.json() is None


# Verify endpoint must be rider-only
def test_owner_verify_forbidden(h):
    r = requests.post(f"{BASE_URL}/api/rider-stock/nonexistent-id/verify", headers=h)
    assert r.status_code == 403
    assert "Rider" in r.json().get("detail", "")


def test_verify_unauthenticated():
    r = requests.post(f"{BASE_URL}/api/rider-stock/nonexistent-id/verify")
    assert r.status_code in (401, 403)


def test_history_unauthenticated():
    r = requests.get(f"{BASE_URL}/api/rider-stock/history", params={"start": "2000-01-01", "end": "2100-01-01"})
    assert r.status_code in (401, 403)


# POST rider-stock with unknown rider -> 404, nothing persisted
def test_owner_save_unknown_rider(h):
    r = requests.post(f"{BASE_URL}/api/rider-stock", json={"rider_id": "TEST_none", "date": "2026-01-01", "items": {}, "photo": None}, headers=h)
    assert r.status_code in (404, 422)


def test_users_only_owner(h):
    r = requests.get(f"{BASE_URL}/api/users", headers=h)
    assert r.status_code == 200
    users = r.json()
    assert [u["username"] for u in users] == ["baa"] or len(users) == 1
