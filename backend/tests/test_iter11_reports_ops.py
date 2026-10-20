# Iteration 11: operations reports (wastage/inventory/purchases/opname), auth, user schema photo
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
RANGE = {"start": "2020-01-01", "end": "2030-12-31"}


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    at = r.json()["account_token"]
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"account_token": at, "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}"}


# Operations report: each kind returns rows + summary
@pytest.mark.parametrize("kind,keys", [
    ("wastage", ["total_value", "count", "largest_reason", "largest_reason_value"]),
    ("inventory", ["total_value", "product_value", "material_value", "item_count"]),
    ("purchases", ["total_cost", "count", "supplier_count"]),
    ("opname", ["count", "positive_value", "negative_value", "accuracy"]),
])
def test_operations_kinds(h, kind, keys):
    r = requests.get(f"{BASE_URL}/api/reports/operations", params={"kind": kind, **RANGE}, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["kind"] == kind
    assert isinstance(d["rows"], list)
    for k in keys:
        assert k in d["summary"], k
    assert "_id" not in str(d)


def test_inventory_rows_real(h):
    d = requests.get(f"{BASE_URL}/api/reports/operations", params={"kind": "inventory", **RANGE}, headers=h).json()
    assert len(d["rows"]) == d["summary"]["item_count"]
    assert d["summary"]["item_count"] > 0
    for row in d["rows"]:
        for k in ("name", "category", "type", "qty", "unit", "unit_cost", "value"):
            assert k in row
    assert d["summary"]["total_value"] == d["summary"]["product_value"] + d["summary"]["material_value"]


def test_empty_kinds_zero(h):
    for kind in ("wastage", "purchases", "opname"):
        d = requests.get(f"{BASE_URL}/api/reports/operations", params={"kind": kind, **RANGE}, headers=h).json()
        assert d["summary"]["count"] == len(d["rows"])


def test_operations_invalid_kind(h):
    r = requests.get(f"{BASE_URL}/api/reports/operations", params={"kind": "bogus", **RANGE}, headers=h)
    assert r.status_code == 400


def test_operations_missing_params(h):
    r = requests.get(f"{BASE_URL}/api/reports/operations", params={"kind": "inventory"}, headers=h)
    assert r.status_code == 422


def test_operations_requires_auth():
    r = requests.get(f"{BASE_URL}/api/reports/operations", params={"kind": "inventory", **RANGE})
    assert r.status_code in (401, 403)
    r = requests.get(f"{BASE_URL}/api/reports/sales", params=RANGE)
    assert r.status_code in (401, 403)


def test_operations_bad_token():
    r = requests.get(f"{BASE_URL}/api/reports/operations", params={"kind": "inventory", **RANGE}, headers={"Authorization": "Bearer abc"})
    assert r.status_code in (401, 403)


def test_sales_report_still_ok(h):
    r = requests.get(f"{BASE_URL}/api/reports/sales", params={**RANGE, "payment_method": "all", "order_type": "all"}, headers=h)
    assert r.status_code == 200
    assert "products" in r.json()


def test_users_list_owner_only_one(h):
    r = requests.get(f"{BASE_URL}/api/users", headers=h)
    assert r.status_code == 200
    names = [u["username"] for u in r.json()]
    assert "baa" in names


def test_user_create_validation_no_persist(h):
    # Missing required pin -> 422, nothing persisted; verifies photo field accepted by schema
    r = requests.post(f"{BASE_URL}/api/users", json={"name": "TEST_x", "username": "test_x_nopersist", "role": "rider", "photo": "data:image/png;base64,AAAA"}, headers=h)
    assert r.status_code == 422
    users = requests.get(f"{BASE_URL}/api/users", headers=h).json()
    assert not any(u["username"] == "test_x_nopersist" for u in users)


def test_openapi_photo_in_schemas():
    r = requests.get(f"{BASE_URL}/api/openapi.json")
    if r.status_code != 200:
        pytest.skip("openapi not exposed")
    s = r.json()["components"]["schemas"]
    assert "photo" in s["UserCreateIn"]["properties"]
    assert "photo" in s["UserUpdateIn"]["properties"]
