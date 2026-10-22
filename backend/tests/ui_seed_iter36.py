# Seed/cleanup temp Rider for iteration 36 UI test. Usage: python ui_seed_iter35.py seed|cleanup
import os
import sys

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

if sys.argv[1] == "seed":
    s = requests.Session()
    tok = s.post(f"{API}/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True}).json()["account_token"]
    s.post(f"{API}/auth/login", json={"account_token": tok, "pin": "130994", "remember": True})
    r = s.post(f"{API}/users", json={"name": "TEST Rider UI36", "username": "test_ui36rider", "pin": "468024", "role": "rider", "active": True})
    print(r.status_code, r.json().get("id"))
else:
    ids = [u["id"] for u in db.users.find({"username": {"$regex": "^test_"}}, {"id": 1})]
    for c in ("rider_stock", "menu_stock_tx", "sales", "eod", "attendance"):
        db[c].delete_many({"rider_id": {"$in": ids}})
    for c in ("sessions", "audit_logs", "files"):
        db[c].delete_many({"user_id": {"$in": ids}})
    print(db.users.delete_many({"id": {"$in": ids}}).deleted_count)
