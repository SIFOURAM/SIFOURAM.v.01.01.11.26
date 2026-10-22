# Iter29: /api/salary rank tiers + live rider sales detail (read-only, no persistent data)
import os
import datetime
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

EXPECTED = [
    ("Herald", 0, 1750000, 20000, 0.0),
    ("Warriors", 1750000, 2520000, 30000, 0.05),
    ("Masters", 2520000, 3220000, 35000, 0.07),
    ("Divine", 3220000, 4000000, 40000, 0.10),
    ("Immortal", 4000000, None, 50000, 0.15),
]


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    acct = r.json().get("account_token") or r.json().get("token")
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"account_token": acct, "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _week():
    t = datetime.date.today()
    s = t - datetime.timedelta(days=t.weekday())
    return {"start": s.isoformat(), "end": (s + datetime.timedelta(days=6)).isoformat()}


@pytest.fixture(scope="module")
def salary(owner_token):
    r = requests.get(f"{BASE_URL}/api/salary", params=_week(), headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200, r.text
    return r.json()


def test_salary_requires_auth():
    r = requests.get(f"{BASE_URL}/api/salary", params=_week())
    assert r.status_code in (401, 403)


def test_tiers_match_thresholds(salary):
    tiers = salary["tiers"]
    assert len(tiers) == 5
    for t, (name, mn, mx, att, pct) in zip(tiers, EXPECTED):
        assert t["name"] == name and t["threshold"] == mn and t["maximum"] == mx
        assert t["attendance_benefit"] == att and t["pct"] == pct


def test_riders_payload_fields(salary):
    assert salary["rider_count"] == len(salary["riders"])
    for r in salary["riders"]:
        for k in ("rider_id", "rider_name", "gross", "tier", "next_tier", "incentive", "allowance"):
            assert k in r
        assert "_id" not in r and "pin_hash" not in str(r)
        if r["next_tier"]:
            nt = r["next_tier"]
            assert 0 <= nt["progress"] <= 100
            assert nt["remaining"] == max(0, nt["threshold"] - r["gross"])
            assert round(min(100, r["gross"] / nt["threshold"] * 100), 1) == nt["progress"]
        else:
            assert r["tier"] == "Immortal"
        # tier must be consistent with gross
        exp = next(n for n, mn, mx, *_ in EXPECTED if mx is None or r["gross"] < mx)
        assert r["tier"] == exp


def test_salary_missing_params(owner_token):
    r = requests.get(f"{BASE_URL}/api/salary", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 422
