# Iter21: Rider Rank weekly target redesign - boundaries for /api/salary & /api/rider-rank, attendance-based allowance, main commission
import os
import uuid
import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
PIN = "246813"

# (gross, rank, attendance_benefit, pct, next_name)
BOUNDARIES = [
    (0, "Herald", 20000, 0.0, "Warriors"),
    (1749999, "Herald", 20000, 0.0, "Warriors"),
    (1750000, "Warriors", 30000, 0.05, "Masters"),
    (2519999, "Warriors", 30000, 0.05, "Masters"),
    (2520000, "Masters", 35000, 0.07, "Divine"),
    (3219999, "Masters", 35000, 0.07, "Divine"),
    (3220000, "Divine", 40000, 0.10, "Immortal"),
    (3999999, "Divine", 40000, 0.10, "Immortal"),
    (4000000, "Immortal", 50000, 0.15, None),
]
NEXT_MIN = {"Warriors": 1750000, "Masters": 2520000, "Divine": 3220000, "Immortal": 4000000}


def login(i, p):
    r = requests.post(f"{API}/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True})
    r = requests.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": p, "remember": True})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def ctx():
    ot = login("baa", "130994")
    oh = {"Authorization": f"Bearer {ot}"}
    r = requests.post(f"{API}/users", headers=oh, json={"name": "TEST QA21 Rider", "username": "qa21_rider", "role": "rider", "pin": PIN})
    assert r.status_code in (200, 201), r.text
    rid = r.json()["id"]
    rt = login("qa21_rider", PIN)
    yield {"oh": oh, "rid": rid, "rh": {"Authorization": f"Bearer {rt}"}}
    mdb.deposits.delete_many({"rider_id": rid})
    mdb.attendance.delete_many({"rider_id": rid})
    mdb.sales.delete_many({"rider_id": rid})
    mdb.users.delete_many({"id": rid})
    mdb.login_attempts.delete_many({"identifier": {"$regex": "qa21_"}})
    mdb.sessions.delete_many({"user_id": rid}) if "sessions" in mdb.list_collection_names() else None


def add_dep(rid, date, amount, cash_share=0.6):
    cash = round(amount * cash_share)
    mdb.deposits.insert_one({"id": str(uuid.uuid4()), "rider_id": rid, "rider_name": "TEST QA21 Rider", "date": date,
                             "total_cups": 1, "total_cash": cash, "total_qris": amount - cash, "net_cash": cash,
                             "rows": [{"name": "TEST_QA21 Kopi", "total_sold": 1}]})


def add_att(rid, date):
    mdb.attendance.insert_one({"id": str(uuid.uuid4()), "rider_id": rid, "rider_name": "TEST QA21 Rider", "date": date})


@pytest.mark.parametrize("idx", range(len(BOUNDARIES)))
def test_boundaries(ctx, idx):
    gross, name, att, pct, nxt = BOUNDARIES[idx]
    # each boundary in its own week in 2019 (Mon..Sun), 2 attendance days
    day0 = 1 + idx * 0  # placeholder
    month = idx + 1
    start, end = f"2019-{month:02d}-01", f"2019-{month:02d}-07"
    if gross:
        add_dep(ctx["rid"], f"2019-{month:02d}-02", gross)
    add_att(ctx["rid"], f"2019-{month:02d}-02")
    add_att(ctx["rid"], f"2019-{month:02d}-03")
    p = {"start": start, "end": end, "rider_id": ctx["rid"]}
    rk = requests.get(f"{API}/rider-rank", headers=ctx["oh"], params=p)
    assert rk.status_code == 200, rk.text
    d = rk.json()
    assert d["gross"] == gross
    assert d["rank"]["name"] == name
    assert d["rank"]["attendance_benefit"] == att
    assert d["rank"]["commission_pct"] == pct
    assert d["attendance_days"] == 2
    assert d["attendance_total"] == att * 2
    assert d["commission"] == round(gross * pct)
    assert d["main_estimated_commission"] == d["attendance_total"] + d["commission"]
    if nxt:
        assert d["rank"]["next"]["name"] == nxt
        assert d["remaining"] == NEXT_MIN[nxt] - gross
    else:
        assert d["rank"]["next"] is None and d["progress"] == 100 and d["remaining"] == 0
    sl = requests.get(f"{API}/salary", headers=ctx["oh"], params=p)
    assert sl.status_code == 200, sl.text
    s = sl.json()
    assert len(s["riders"]) == 1
    r = s["riders"][0]
    assert r["tier"] == name and r["incentive_pct"] == pct
    assert r["allowance"] == att * 2 and r["attendance_days"] == 2 and r["allowance_days"] == 2
    assert r["incentive"] == round(gross * pct)
    assert r["total_income"] == d["main_estimated_commission"]
    assert [t["name"] for t in s["tiers"]] == ["Herald", "Warriors", "Masters", "Divine", "Immortal"]


def test_allowance_uses_attendance_not_sales_days(ctx):
    rid = ctx["rid"]
    # 3 sale days, 1 attendance day -> Warriors (2,000,000) allowance = 30,000
    for dd, amt in [("2019-11-04", 700000), ("2019-11-05", 700000), ("2019-11-06", 600000)]:
        add_dep(rid, dd, amt)
    add_att(rid, "2019-11-04")
    p = {"start": "2019-11-04", "end": "2019-11-10", "rider_id": rid}
    r = requests.get(f"{API}/salary", headers=ctx["oh"], params=p).json()["riders"][0]
    assert r["gross"] == 2000000 and r["tier"] == "Warriors"
    assert r["sales_days"] == 3 and r["attendance_days"] == 1
    assert r["allowance"] == 30000
    assert r["incentive"] == 100000 and r["total_income"] == 130000
    # 0 sales, 4 attendance -> Herald 80,000
    for dd in ["2019-12-02", "2019-12-03", "2019-12-04", "2019-12-05"]:
        add_att(rid, dd)
    p2 = {"start": "2019-12-02", "end": "2019-12-08", "rider_id": rid}
    r2 = requests.get(f"{API}/salary", headers=ctx["oh"], params=p2).json()["riders"][0]
    assert r2["allowance"] == 80000 and r2["incentive"] == 0 and r2["tier"] == "Herald"
    rk = requests.get(f"{API}/rider-rank", headers=ctx["oh"], params=p2).json()
    assert rk["main_estimated_commission"] == 80000


def test_rider_role_scoped_and_missing_rider(ctx):
    p = {"start": "2019-11-04", "end": "2019-11-10"}
    r = requests.get(f"{API}/rider-rank", headers=ctx["rh"], params={**p, "rider_id": "someone-else"})
    assert r.status_code == 200 and r.json()["rider_id"] == ctx["rid"]
    assert r.json()["gross"] == 2000000
    r = requests.get(f"{API}/rider-rank", headers=ctx["oh"], params=p)
    assert r.status_code == 400
    r = requests.get(f"{API}/rider-rank", params={**p, "rider_id": ctx["rid"]})
    assert r.status_code in (401, 403)
