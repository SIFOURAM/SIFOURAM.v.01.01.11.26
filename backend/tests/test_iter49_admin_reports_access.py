# Iter49: Admin access to finance summary + gps active (REPORTS = owner+admin)
import os
import datetime
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
TODAY = datetime.date.today().isoformat()


def login(ident, pin):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": ident, "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    tok = r.json().get("account_token")
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": tok, "pin": pin, "remember": True})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def owner():
    return login("baa", "130994")


@pytest.fixture(scope="module")
def admin():
    return login("dummy_admin", "100002")


@pytest.fixture(scope="module")
def barteam():
    try:
        return login("dummy_barteam", "100003")
    except AssertionError:
        pytest.skip("barteam login failed")


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_finance_summary_allowed(request, who):
    s = request.getfixturevalue(who)
    r = s.get(f"{BASE_URL}/api/finance/summary", params={"start": TODAY, "end": TODAY})
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), dict)


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_gps_active_allowed(request, who):
    s = request.getfixturevalue(who)
    r = s.get(f"{BASE_URL}/api/gps/active", params={"date": TODAY})
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


def test_finance_summary_denied_barteam(barteam):
    r = barteam.get(f"{BASE_URL}/api/finance/summary", params={"start": TODAY, "end": TODAY})
    assert r.status_code == 403


def test_gps_active_denied_barteam(barteam):
    r = barteam.get(f"{BASE_URL}/api/gps/active", params={"date": TODAY})
    assert r.status_code == 403


def test_finance_unauth():
    r = requests.get(f"{BASE_URL}/api/finance/summary", params={"start": TODAY, "end": TODAY})
    assert r.status_code == 401
