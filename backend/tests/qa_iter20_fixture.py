# Iter20 UI helper: temp barteam + rider(with WA); prints tokens. Usage: python qa_iter20_fixture.py setup|cleanup
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
STATE = "/tmp/qa_iter20_state.json"
PIN = "246813"


def login(i, p):
    r = requests.post(f"{API}/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True})
    r = requests.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": p, "remember": True})
    return r.json()["token"]


if sys.argv[1] == "setup":
    files_before = [f["id"] for f in mdb.files.find({}, {"_id": 0, "id": 1})]
    ot = login("baa", "130994")
    o = {"Authorization": f"Bearer {ot}"}
    out = {"owner_token": ot, "files_before": files_before, "users": {}}
    for role in ["barteam", "rider"]:
        un = f"qa20ui_{role}"
        u = requests.post(f"{API}/users", headers=o, json={"name": f"TEST QA20 {role}", "username": un, "role": role, "pin": PIN, "whatsapp": "081299998888"}).json()
        out["users"][role] = u["id"]
        out[f"{role}_token"] = login(un, PIN)
    json.dump(out, open(STATE, "w"))
    print(json.dumps({k: v for k, v in out.items() if k != "files_before"}))
else:
    st = json.load(open(STATE))
    ids = list(st["users"].values())
    print("po", mdb.purchase_orders.delete_many({"$or": [{"requested_by": {"$in": ids}}, {"note": {"$regex": "TEST_QA20"}}]}).deleted_count)
    print("notif", mdb.notifications.delete_many({"$or": [{"for_user": {"$in": ids}}, {"body": {"$regex": "TEST_QA20|TEST QA20"}}, {"title": {"$regex": "TEST_QA20"}}]}).deleted_count)
    print("pay", mdb.payment_accounts.delete_many({"name": {"$regex": "^TEST_QA20"}}).deleted_count)
    print("files", mdb.files.delete_many({"id": {"$nin": st["files_before"]}, "folder": "payment_accounts"}).deleted_count)
    print("users", mdb.users.delete_many({"id": {"$in": ids}}).deleted_count)
    mdb.login_attempts.delete_many({"identifier": {"$regex": "qa20ui_"}})
