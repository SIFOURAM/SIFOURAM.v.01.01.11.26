# Iteration 13: Owner login flow + reports access (read-only, no data persisted)
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
TODAY = "2026-01-15"


@pytest.fixture(scope="module")
def owner_token():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    tok = r.json()["account_token"]
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": tok, "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["role"] == "owner"
    return data["token"]


def h(t):
    return {"Authorization": f"Bearer {t}"}


# Auth
def test_identify_without_consent_rejected():
    r = requests.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": False, "privacy_accepted": False})
    assert r.status_code in (400, 422)


def test_me(owner_token):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=h(owner_token))
    assert r.status_code == 200
    assert r.json()["role"] == "owner"
    assert "pin_hash" not in r.json() and "password_hash" not in r.json()


# Reports
def test_sales_report_owner(owner_token):
    r = requests.get(f"{BASE_URL}/api/reports/sales", params={"start": TODAY, "end": TODAY}, headers=h(owner_token))
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("transactions", "revenue", "average_order", "discount"):
        assert k in d


@pytest.mark.parametrize("kind", ["wastage", "inventory", "purchases", "opname"])
def test_operations_report_owner(owner_token, kind):
    r = requests.get(f"{BASE_URL}/api/reports/operations", params={"kind": kind, "start": TODAY, "end": TODAY}, headers=h(owner_token))
    assert r.status_code == 200, r.text
    assert "rows" in r.json()


def test_reports_unauthenticated():
    r = requests.get(f"{BASE_URL}/api/reports/sales", params={"start": TODAY, "end": TODAY})
    assert r.status_code in (401, 403)


def test_dashboard_summary_owner(owner_token):
    r = requests.get(f"{BASE_URL}/api/dashboard/summary", params={"start": TODAY, "end": TODAY}, headers=h(owner_token))
    assert r.status_code == 200, r.text


# Source-level: REPORTS dependency includes owner and admin
def test_reports_dependency_roles():
    src = open("/app/backend/server.py").read()
    assert re.search(r'REPORTS\s*=\s*roles\("owner",\s*"admin"\)', src)
    assert 'u=Depends(REPORTS)' in src.split('@api.get("/reports/sales")')[1].split("@api")[0]
    assert 'u=Depends(REPORTS)' in src.split('@api.get("/reports/operations")')[1].split("@api")[0]
