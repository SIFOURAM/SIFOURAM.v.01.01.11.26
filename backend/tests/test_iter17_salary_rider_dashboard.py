# Iter17: regression for GET /api/salary (JSON serialization of top tier) + rider-dashboard dependent endpoints (read-only)
import math
import os
import json
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def token():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    acct = r.json().get("account_token")
    assert acct
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": acct, "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}"}


RANGES = [("2026-01-01", "2026-01-01"), ("2026-01-01", "2026-01-31"), ("2025-01-01", "2026-12-31")]


def _check_finite(obj):
    if isinstance(obj, float):
        assert math.isfinite(obj), f"non-finite value {obj}"
    elif isinstance(obj, dict):
        for v in obj.values():
            _check_finite(v)
    elif isinstance(obj, list):
        for v in obj:
            _check_finite(v)


# Salary endpoint: no 500, valid structure, finite values
@pytest.mark.parametrize("start,end", RANGES)
def test_salary_no_500_and_structure(h, start, end):
    r = requests.get(f"{BASE_URL}/api/salary", params={"start": start, "end": end}, headers=h)
    assert r.status_code == 200, r.text
    # strict JSON parse (rejects Infinity/NaN)
    data = json.loads(r.text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert set(["riders", "tiers", "rider_count"]) <= set(data.keys())
    assert isinstance(data["riders"], list)
    assert data["rider_count"] == len(data["riders"])
    _check_finite(data)


def test_salary_tiers_last_is_finite_int(h):
    r = requests.get(f"{BASE_URL}/api/salary", params={"start": "2026-01-01", "end": "2026-01-31"}, headers=h)
    assert r.status_code == 200
    tiers = r.json()["tiers"]
    assert [t["name"] for t in tiers] == ["Herald", "Warriors", "Masters", "Divine", "Immortal"]
    last = tiers[-1]
    assert isinstance(last["threshold"], int)
    assert last["threshold"] > 4000000
    for t in tiers:
        assert isinstance(t["pct"], (int, float)) and math.isfinite(t["pct"])
    ths = [t["threshold"] for t in tiers]
    assert ths == sorted(ths)


def test_salary_rider_fields(h):
    r = requests.get(f"{BASE_URL}/api/salary", params={"start": "2025-01-01", "end": "2026-12-31"}, headers=h)
    data = r.json()
    for rd in data["riders"]:
        for k in ["rider_id", "rider_name", "gross", "tier", "incentive", "allowance", "total_income", "next_tier"]:
            assert k in rd
        if rd["next_tier"]:
            assert math.isfinite(rd["next_tier"]["progress"])


def test_salary_unauth():
    r = requests.get(f"{BASE_URL}/api/salary", params={"start": "2026-01-01", "end": "2026-01-31"})
    assert r.status_code in (401, 403)


def test_salary_missing_params(h):
    r = requests.get(f"{BASE_URL}/api/salary", headers=h)
    assert r.status_code == 422


def test_salary_unknown_rider(h):
    r = requests.get(f"{BASE_URL}/api/salary", params={"start": "2026-01-01", "end": "2026-01-31", "rider_id": "nonexistent"}, headers=h)
    assert r.status_code == 200
    assert r.json()["rider_count"] == 0


# Other endpoints loaded by RiderDashboard
@pytest.mark.parametrize("path", ["/dashboard/summary", "/rider-stock/history", "/sales", "/deposits"])
def test_rider_dashboard_deps(h, path):
    r = requests.get(f"{BASE_URL}/api{path}", params={"start": "2026-01-01", "end": "2026-01-31"}, headers=h)
    assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"


def test_users_rider_list(h):
    r = requests.get(f"{BASE_URL}/api/users", params={"role": "rider"}, headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
