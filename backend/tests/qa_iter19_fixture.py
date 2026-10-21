# Iter19 helper for UI: temp QA rider + unverified stock for a date; prints tokens. Usage: python qa_iter19_fixture.py setup <date>|cleanup
import os
import sys
import json
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
STATE = "/tmp/qa_iter19_state.json"
PIN = "246813"
UNAME = "qa_rider_ui19"
PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def login(i, p):
    r = requests.post(f"{API}/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True})
    r = requests.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": p, "remember": True})
    return r.json()["token"]


cmd = sys.argv[1]
if cmd == "setup":
    date = sys.argv[2]
    snap = {m["id"]: m.get("stock", 0) for m in mdb.menus.find({}, {"_id": 0})}
    files_before = [f["id"] for f in mdb.files.find({}, {"_id": 0, "id": 1})]
    ot = login("baa", "130994")
    o = {"Authorization": f"Bearer {ot}"}
    r = requests.post(f"{API}/users", headers=o, json={"name": "TEST QA Rider UI19", "username": UNAME, "role": "rider", "pin": PIN}).json()
    items = {m["id"]: 3 for m in mdb.menus.find({}, {"_id": 0})}
    s = requests.post(f"{API}/rider-stock", headers=o, json={"rider_id": r["id"], "date": date, "items": items, "photo": PHOTO}).json()
    rt = login(UNAME, PIN)
    json.dump({"rider_id": r["id"], "stock_id": s["id"], "snap": snap, "files_before": files_before}, open(STATE, "w"))
    print(json.dumps({"rider_id": r["id"], "stock_id": s["id"], "owner_token": ot, "rider_token": rt}))
elif cmd == "cleanup":
    st = json.load(open(STATE))
    rid = st["rider_id"]
    for c in ["sales", "rider_stock", "attendance", "eod", "gps", "deposits"]:
        print(c, mdb[c].delete_many({"rider_id": rid}).deleted_count)
    print("files", mdb.files.delete_many({"id": {"$nin": st["files_before"]}}).deleted_count)
    print("customers", mdb.customers.delete_many({"name": {"$regex": "^TEST_"}}).deleted_count)
    mdb.login_attempts.delete_many({"identifier": {"$regex": f"{rid}|{UNAME}"}})
    print("user", mdb.users.delete_one({"id": rid}).deleted_count)
    for mid, v in st["snap"].items():
        mdb.menus.update_one({"id": mid}, {"$set": {"stock": v}})
