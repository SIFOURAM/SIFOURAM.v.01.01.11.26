# Iter23: Stock Rider history scope, Pengambilan verify rules, Sisa range endpoint. Requires qa_iter23_fixture.py setup.
import os
import json
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    from dotenv import load_dotenv
    load_dotenv("/app/frontend/.env")
    BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = BASE_URL + "/api"
ST = json.load(open("/tmp/qa_iter23_state.json"))
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
H = lambda t: {"Authorization": f"Bearer {t}"}
A, B = ST["riders"]


# Auth two-step
def test_two_step_login_owner():
    r = requests.post(f"{API}/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200 and r.json().get("account_token")
    r2 = requests.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": "130994", "remember": True})
    assert r2.status_code == 200 and r2.json()["user"]["role"] == "owner"
    me = requests.get(f"{API}/auth/me", headers=H(r2.json()["token"]))
    assert me.status_code == 200


# Stock Rider history
def test_owner_history_scoped_by_rider_and_range():
    r = requests.get(f"{API}/rider-stock/history", headers=H(ST["owner_token"]), params={"rider_id": A, "start": ST["yday"], "end": ST["today"]})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2 and all(x["rider_id"] == A for x in rows)
    assert rows[0]["date"] == ST["today"] and rows[0]["photo"] and rows[0]["pic_name"] and rows[0]["total"] == 15
    assert rows[0]["detail"] and sum(rows[0]["detail"].values()) == 15
    r = requests.get(f"{API}/rider-stock/history", headers=H(ST["owner_token"]), params={"rider_id": A, "start": ST["today"], "end": ST["today"]})
    assert len(r.json()) == 1


def test_rider_history_forced_to_self():
    r = requests.get(f"{API}/rider-stock/history", headers=H(ST["rider_b_token"]), params={"rider_id": A, "start": ST["yday"], "end": ST["today"]})
    assert r.status_code == 200 and r.json() and all(x["rider_id"] == B for x in r.json())


def test_rider_cannot_get_other_rider_stock():
    r = requests.get(f"{API}/rider-stock", headers=H(ST["rider_b_token"]), params={"rider_id": A, "date": ST["today"]})
    assert r.status_code == 403


# Pengambilan verify
def test_owner_cannot_verify():
    sid = ST["stocks"][f"{B}:{ST['today']}"]
    r = requests.post(f"{API}/rider-stock/{sid}/verify", headers=H(ST["owner_token"]), json={"photo": PNG})
    assert r.status_code == 403


def test_other_rider_cannot_verify():
    sid = ST["stocks"][f"{B}:{ST['today']}"]
    r = requests.post(f"{API}/rider-stock/{sid}/verify", headers=H(ST["rider_a_token"]), json={"photo": PNG})
    assert r.status_code == 404


def test_verify_requires_image():
    sid = ST["stocks"][f"{B}:{ST['today']}"]
    r = requests.post(f"{API}/rider-stock/{sid}/verify", headers=H(ST["rider_b_token"]), json={"photo": "hello"})
    assert r.status_code == 400


def test_verified_stock_fills_pos():
    r = requests.get(f"{API}/pos/stock", headers=H(ST["rider_a_token"]), params={"rider_id": A, "date": ST["today"]})
    d = r.json()
    assert d["has_stock"] is True
    m1 = next(i for i in d["items"] if i["menu_id"] == ST["m1"])
    assert m1["initial"] == 10 and m1["sold"] == 2 and m1["remaining"] == 8


def test_unverified_stock_pending_in_pos():
    r = requests.get(f"{API}/pos/stock", headers=H(ST["rider_b_token"]), params={"rider_id": B, "date": ST["today"]})
    d = r.json()
    assert d["has_stock"] is False and d["pending_stock"] is True


# Sisa
def test_remaining_single_date():
    r = requests.get(f"{API}/rider-stock/remaining", headers=H(ST["owner_token"]), params={"date": ST["today"], "rider_id": A})
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["initial_total"] == 15 and row["sold_total"] == 3 and row["remaining_total"] == 12 and row["difference_total"] == 0


def test_remaining_range_per_row_values():
    r = requests.get(f"{API}/rider-stock/remaining", headers=H(ST["owner_token"]), params={"start": ST["yday"], "end": ST["today"], "rider_id": A})
    assert r.status_code == 200
    rows = {x["stock_id"]: x for x in r.json()}
    assert len(rows) == 2
    t = rows[ST["stocks"][f"{A}:{ST['today']}"]]
    y = rows[ST["stocks"][f"{A}:{ST['yday']}"]]
    assert (t["initial_total"], t["sold_total"], t["remaining_total"], t["difference_total"]) == (15, 3, 12, 0), t
    assert (y["initial_total"], y["sold_total"], y["remaining_total"], y["difference_total"]) == (12, 3, 9, 0), y
    ym1 = next(i for i in y["items"] if i["menu_id"] == ST["m1"])
    assert (ym1["initial"], ym1["sold"], ym1["remaining"]) == (8, 3, 5)


def test_remaining_rows_have_date():
    r = requests.get(f"{API}/rider-stock/remaining", headers=H(ST["owner_token"]), params={"start": ST["yday"], "end": ST["today"]})
    rows = r.json()
    assert len(rows) == 4
    assert all("date" in x for x in rows), "row.date missing — UI renders fmtDate(row.date)"


def test_remaining_rider_scoped():
    r = requests.get(f"{API}/rider-stock/remaining", headers=H(ST["rider_b_token"]), params={"start": ST["yday"], "end": ST["today"], "rider_id": A})
    assert all(x["rider_id"] == B for x in r.json())


def test_remaining_requires_dates():
    r = requests.get(f"{API}/rider-stock/remaining", headers=H(ST["owner_token"]))
    assert r.status_code == 400
