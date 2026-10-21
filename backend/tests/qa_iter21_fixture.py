# Iter21 UI helper: temp rider w/ this-week deposit (Masters) + attendance + old manual-date deposit. Usage: setup|cleanup
import os
import sys
import json
import uuid
import datetime
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
STATE = "/tmp/qa_iter21_state.json"
PIN = "246813"


def login(i, p):
    r = requests.post(f"{API}/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True})
    r = requests.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": p, "remember": True})
    return r.json()["token"]


def dep(rid, date, amount):
    mdb.deposits.insert_one({"id": str(uuid.uuid4()), "rider_id": rid, "rider_name": "TEST QA21UI Rider", "date": date, "total_cups": 9,
                             "total_cash": amount // 2, "total_qris": amount - amount // 2, "net_cash": amount // 2,
                             "rows": [{"name": "TEST_QA21 Kopi", "total_sold": 9}], "created_at": date + "T08:00:00"})


if sys.argv[1] == "setup":
    today = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime("%Y-%m-%d")
    ot = login("baa", "130994")
    u = requests.post(f"{API}/users", headers={"Authorization": f"Bearer {ot}"}, json={"name": "TEST QA21UI Rider", "username": "qa21ui_rider", "role": "rider", "pin": PIN}).json()
    rid = u["id"]
    dep(rid, today, 2600000)
    dep(rid, "2019-11-05", 1800000)
    mdb.attendance.insert_one({"id": str(uuid.uuid4()), "rider_id": rid, "rider_name": "TEST QA21UI Rider", "date": today})
    out = {"owner_token": ot, "rider_token": login("qa21ui_rider", PIN), "rider_id": rid, "today": today}
    json.dump(out, open(STATE, "w"))
    print(json.dumps(out))
else:
    st = json.load(open(STATE))
    rid = st["rider_id"]
    print("dep", mdb.deposits.delete_many({"rider_id": rid}).deleted_count)
    print("att", mdb.attendance.delete_many({"rider_id": rid}).deleted_count)
    print("wd", mdb.withdrawals.delete_many({"rider_id": rid}).deleted_count)
    print("users", mdb.users.delete_many({"id": rid}).deleted_count)
    mdb.login_attempts.delete_many({"identifier": {"$regex": "qa21ui_"}})
