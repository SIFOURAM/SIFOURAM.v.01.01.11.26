# POS Dashboard (/api/reports/sales) regression tests - read-only, no data creation
import os
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def token():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    d = r.json()
    acct = d.get("account_token") or d.get("token")
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": acct, "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "owner"
    return r.json()["token"]


def _get(token, start, end, **kw):
    params = {"start": start, "end": end, "payment_method": "all", "order_type": "all", **kw}
    return requests.get(f"{BASE_URL}/api/reports/sales", params=params, headers={"Authorization": f"Bearer {token}"})


# Owner can read sales report for today
def test_sales_today_owner(token):
    t = date.today().isoformat()
    r = _get(token, t, t)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["revenue", "transactions", "daily_revenue", "payment_distribution"]:
        assert k in d
    assert isinstance(d["daily_revenue"], list)
    assert isinstance(d["payment_distribution"], list)
    assert "_id" not in str(d)


# Month range and consistency: sum of payment = revenue = sum of daily
@pytest.mark.parametrize("days", [0, 1, 7, 31, 62])
def test_sales_ranges_consistent(token, days):
    end = date.today()
    start = end - timedelta(days=days)
    r = _get(token, start.isoformat(), end.isoformat())
    assert r.status_code == 200
    d = r.json()
    assert round(sum(x["value"] for x in d["payment_distribution"])) == round(d["revenue"])
    assert round(sum(x["revenue"] for x in d["daily_revenue"])) == round(d["revenue"])
    for x in d["payment_distribution"]:
        assert x["name"] == x["name"].upper()


# No auth rejected
def test_sales_requires_auth():
    t = date.today().isoformat()
    r = requests.get(f"{BASE_URL}/api/reports/sales", params={"start": t, "end": t})
    assert r.status_code in (401, 403)


# Missing params -> 422
def test_sales_missing_params(token):
    r = requests.get(f"{BASE_URL}/api/reports/sales", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422
