# Iter23 helper: 2 temp riders, rider_stock on today + yesterday (via API), verify one, insert sales. Usage: setup|cleanup
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
STATE = "/tmp/qa_iter23_state.json"
PIN = "246813"
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def login(i, p):
    r = requests.post(f"{API}/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True})
    r = requests.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": p, "remember": True})
    return r.json()["token"]


if sys.argv[1] == "setup":
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    today, yday = now.strftime("%Y-%m-%d"), (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    menus = list(mdb.menus.find({"active": {"$ne": False}}, {"_id": 0}).sort("order", 1))
    menu_stock = {m["id"]: m.get("stock", 0) for m in mdb.menus.find({}, {"_id": 0})}
    ot = login("baa", "130994")
    H = {"Authorization": f"Bearer {ot}"}
    riders = []
    for n in ("a", "b"):
        u = requests.post(f"{API}/users", headers=H, json={"name": f"TEST QA23 Rider {n.upper()}", "username": f"qa23_rider_{n}", "role": "rider", "pin": PIN}).json()
        riders.append(u["id"])
    m1, m2 = menus[0]["id"], menus[1]["id"]
    stocks = {}
    for rid in riders:
        for d, q in ((today, {m1: 10, m2: 5}), (yday, {m1: 8, m2: 4})):
            r = requests.post(f"{API}/rider-stock", headers=H, json={"rider_id": rid, "date": d, "items": q, "photo": PNG})
            stocks[f"{rid}:{d}"] = r.json()["id"]
    rt = login("qa23_rider_a", PIN)
    # rider A verifies both days
    for d in (today, yday):
        requests.post(f"{API}/rider-stock/{stocks[riders[0] + ':' + d]}/verify", headers={"Authorization": f"Bearer {rt}"}, json={"photo": PNG})
    # sales for rider A: yesterday 3 cups m1, today 2 cups m1 + 1 m2
    for d, its in ((yday, [{"menu_id": m1, "qty": 3}]), (today, [{"menu_id": m1, "qty": 2}, {"menu_id": m2, "qty": 1}])):
        mdb.sales.insert_one({"id": str(uuid.uuid4()), "rider_id": riders[0], "date": d, "items": its, "total": 0, "payment_method": "cash", "qa23": True})
    out = {"owner_token": ot, "rider_a_token": rt, "rider_b_token": login("qa23_rider_b", PIN), "riders": riders, "stocks": stocks,
           "today": today, "yday": yday, "m1": m1, "m2": m2, "menu_stock": menu_stock}
    json.dump(out, open(STATE, "w"))
    print(json.dumps({k: v for k, v in out.items() if k != "menu_stock"}))
else:
    st = json.load(open(STATE))
    for rid in st["riders"]:
        print("stock", mdb.rider_stock.delete_many({"rider_id": rid}).deleted_count)
        print("sales", mdb.sales.delete_many({"rider_id": rid}).deleted_count)
        mdb.users.delete_many({"id": rid})
    for mid, s in st["menu_stock"].items():
        mdb.menus.update_one({"id": mid}, {"$set": {"stock": s}})
    mdb.login_attempts.delete_many({"identifier": {"$regex": "qa23_"}})
    print("cleaned")
