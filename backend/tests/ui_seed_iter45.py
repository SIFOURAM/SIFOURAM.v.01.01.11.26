# Iteration 45 UI seed/cleanup: creates one requested PO by dummy_barteam; `cleanup` removes QA data and restores stock
import json
import os
import sys

import requests
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
db = MongoClient("mongodb://localhost:27017")["test_database"]
STATE = "/tmp/iter45_state.json"


def login(i, p):
    s = requests.Session()
    t = s.post(f"{BASE}/api/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True}).json()["account_token"]
    s.post(f"{BASE}/api/auth/login", json={"account_token": t, "pin": p})
    return s


if sys.argv[1] == "seed":
    mats = list(db.materials.find({}, {"_id": 0}).limit(2))
    counters = {c["key"]: c["value"] for c in db.counters.find({"key": {"$regex": "^purchase-order:"}}, {"_id": 0})}
    bar = login("dummy_barteam", "100003")
    po = bar.post(f"{BASE}/api/purchase-orders", json={"items": [{"material_id": mats[0]["id"], "qty": 2, "unit_price": 1000}], "vendor_name": "TEST_vendor", "note": "TEST_QA_UI"}).json()
    json.dump({"po": po["id"], "po_number": po["po_number"], "mats": [{"id": m["id"], "name": m["name"], "stock": m.get("stock", 0), "pack_price": m.get("pack_price")} for m in mats], "counters": counters}, open(STATE, "w"))
    print(po["id"], po["po_number"], [(m["name"], m.get("stock")) for m in mats])
elif sys.argv[1] == "status":
    st = json.load(open(STATE))
    po = db.purchase_orders.find_one({"id": st["po"]}, {"_id": 0, "purchase_proof_data": 0, "arrival_proof_data": 0})
    print(json.dumps({k: po.get(k) for k in ["status", "purchase_vendor", "purchase_date", "purchase_note", "purchase_items"]}, default=str))
    print("has_proof", bool(db.purchase_orders.find_one({"id": st["po"]}).get("purchase_proof_data")))
    for m in st["mats"]:
        print(m["name"], "before", m["stock"], "now", db.materials.find_one({"id": m["id"]})["stock"])
else:
    st = json.load(open(STATE))
    db.inventory_tx.delete_many({"purchase_order_id": st["po"]})
    db.notifications.delete_many({"ref_id": st["po"]})
    db.purchase_orders.delete_one({"id": st["po"]})
    for m in st["mats"]:
        db.materials.update_one({"id": m["id"]}, {"$set": {"stock": m["stock"], "pack_price": m["pack_price"]}})
    for c in db.counters.find({"key": {"$regex": "^purchase-order:"}}):
        if c["key"] in st["counters"]:
            db.counters.update_one({"key": c["key"]}, {"$set": {"value": st["counters"][c["key"]]}})
        else:
            db.counters.delete_one({"key": c["key"]})
    print("cleaned")
