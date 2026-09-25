"""Iteration 9: verify PUT /users/{id} (superadmin only) + POST /inventory/wastage."""
import os
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://advanced-pos-system.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

SUPER = {"identifier": "baa", "password": "Nai130994", "remember": True}
RIDER = {"identifier": "fikar", "password": "Jkt221112", "remember": True}

# 1x1 transparent png data URL
PIX = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_headers():
    return {"Authorization": f"Bearer {_login(SUPER)}"}


@pytest.fixture(scope="module")
def rider_headers():
    return {"Authorization": f"Bearer {_login(RIDER)}"}


# --- Users listing + admin update ---
def test_users_list_superadmin(super_headers):
    r = requests.get(f"{API}/users", headers=super_headers, timeout=15)
    assert r.status_code == 200
    users = r.json()
    assert isinstance(users, list) and len(users) > 0
    assert any(u.get("username") == "baa" for u in users)


def test_admin_update_user_persists(super_headers):
    users = requests.get(f"{API}/users", headers=super_headers, timeout=15).json()
    target = next(u for u in users if u["username"] == "ricky")
    orig_wa = target.get("whatsapp", "")
    new_wa = "628" + str(1000000000 + (hash(orig_wa) % 1000000))
    r = requests.put(f"{API}/users/{target['id']}", headers=super_headers,
                     json={"whatsapp": new_wa}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("whatsapp") == new_wa
    # persistence
    users2 = requests.get(f"{API}/users", headers=super_headers, timeout=15).json()
    t2 = next(u for u in users2 if u["id"] == target["id"])
    assert t2["whatsapp"] == new_wa
    # revert
    requests.put(f"{API}/users/{target['id']}", headers=super_headers, json={"whatsapp": orig_wa}, timeout=15)


def test_rider_cannot_update_user(rider_headers, super_headers):
    users = requests.get(f"{API}/users", headers=super_headers, timeout=15).json()
    tid = next(u for u in users if u["username"] == "ricky")["id"]
    r = requests.put(f"{API}/users/{tid}", headers=rider_headers, json={"name": "X"}, timeout=15)
    assert r.status_code in (401, 403)


# --- Wastage ---
def test_wastage_deducts_stock(super_headers):
    menus = requests.get(f"{API}/menus", headers=super_headers, timeout=15).json()
    m = next((x for x in menus if x.get("stock", 0) >= 5), menus[0])
    before = m["stock"]
    r = requests.post(f"{API}/inventory/wastage", headers=super_headers,
                      json={"menu_id": m["id"], "qty": 1, "photo": PIX, "note": "TEST_iter9"},
                      timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["menu_name"] == m["name"]
    assert d["qty"] == 1
    assert d["before"] == before
    assert d["after"] == before - 1
    assert d.get("photo_url")
    # verify menu stock updated
    menus2 = requests.get(f"{API}/menus", headers=super_headers, timeout=15).json()
    m2 = next(x for x in menus2 if x["id"] == m["id"])
    assert m2["stock"] == before - 1


def test_wastage_requires_photo(super_headers):
    menus = requests.get(f"{API}/menus", headers=super_headers, timeout=15).json()
    m = menus[0]
    r = requests.post(f"{API}/inventory/wastage", headers=super_headers,
                      json={"menu_id": m["id"], "qty": 1, "photo": ""}, timeout=15)
    assert r.status_code in (400, 422)


def test_wastage_rider_forbidden(rider_headers, super_headers):
    menus = requests.get(f"{API}/menus", headers=super_headers, timeout=15).json()
    m = menus[0]
    r = requests.post(f"{API}/inventory/wastage", headers=rider_headers,
                     json={"menu_id": m["id"], "qty": 1, "photo": PIX}, timeout=15)
    assert r.status_code == 403
