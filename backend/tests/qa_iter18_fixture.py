# Iter18 helper: create/verify/cleanup a temporary QA rider + stock for UI testing. Usage: python qa_iter18_fixture.py setup|verify|cleanup
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
STATE = "/tmp/qa_iter18_state.json"
PIN = "246813"
UNAME = "qa_rider_ui18"
PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def login(i, p):
    r = requests.post(f"{API}/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True})
    r = requests.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": p, "remember": True})
    return {"Authorization": f"Bearer {r.json()['token']}"}


cmd, date = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
if cmd == "setup":
    snap = {m["id"]: m.get("stock", 0) for m in mdb.menus.find({}, {"_id": 0})}
    o = login("baa", "130994")
    r = requests.post(f"{API}/users", headers=o, json={"name": "TEST QA Rider UI", "username": UNAME, "role": "rider", "pin": PIN}).json()
    items = {m["id"]: 10 for m in mdb.menus.find({}, {"_id": 0})}
    s = requests.post(f"{API}/rider-stock", headers=o, json={"rider_id": r["id"], "date": date, "items": items, "photo": PHOTO}).json()
    json.dump({"rider_id": r["id"], "stock_id": s["id"], "snap": snap}, open(STATE, "w"))
    print(json.dumps({"rider_id": r["id"], "stock_id": s["id"]}))
elif cmd == "verify":
    st = json.load(open(STATE))
    print(requests.post(f"{API}/rider-stock/{st['stock_id']}/verify", headers=login(UNAME, PIN)).status_code)
elif cmd == "cleanup":
    st = json.load(open(STATE))
    rid = st["rider_id"]
    for c in ["sales", "rider_stock", "attendance", "eod", "gps", "files"]:
        key = "user_id" if c == "files" else "rider_id"
        print(c, mdb[c].delete_many({key: rid}).deleted_count)
    print("customers", mdb.customers.delete_many({"name": {"$regex": "^TEST_"}}).deleted_count)
    mdb.login_attempts.delete_many({"identifier": {"$regex": rid}})
    print("user", mdb.users.delete_one({"id": rid}).deleted_count)
    for mid, v in st["snap"].items():
        mdb.menus.update_one({"id": mid}, {"$set": {"stock": v}})
