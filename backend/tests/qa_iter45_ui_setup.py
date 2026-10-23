# Iteration 45 UI QA helper: setup (seed TEST PO + snapshot) / cleanup (restore stock, delete PO data)
import json
import os
import sys

import requests
from PIL import Image, ImageDraw
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
STATE = "/tmp/qa_iter45_state.json"


def _env(key):
    for line in open("/app/backend/.env"):
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')


db = MongoClient(_env("MONGO_URL"))[_env("DB_NAME")]


def login(identifier, pin):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": identifier, "terms_accepted": True, "privacy_accepted": True})
    tok = r.json().get("account_token") or r.json().get("token")
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": tok, "pin": pin, "remember": False})
    assert r.status_code == 200, r.text
    return s


def setup():
    img = Image.new("RGB", (300, 300), "white")
    d = ImageDraw.Draw(img)
    for i in range(0, 300, 15):
        d.line([(0, i), (300, 300 - i)], fill=(i % 255, 50, 200), width=4)
    d.text((20, 140), "TEST STRUK QA 15000", fill="black")
    img.save("/tmp/qa_proof.png")
    bar = login("dummy_barteam", "100003")
    mats = bar.get(f"{BASE_URL}/api/materials").json()
    m0, m1 = mats[0], mats[1]
    counters = {c["key"]: c["value"] for c in db.counters.find({"key": {"$regex": "^purchase-order:"}}, {"_id": 0})}
    snap = {m["id"]: {"stock": m.get("stock", 0), "pack_price": m.get("pack_price")} for m in (m0, m1)}
    existing = [p["id"] for p in db.purchase_orders.find({}, {"id": 1})]
    r = bar.post(f"{BASE_URL}/api/purchase-orders", json={"items": [{"material_id": m0["id"], "qty": 2, "unit_price": 1000}], "vendor_name": "TEST_vendor_ui", "note": "TEST_QA_UI"})
    assert r.status_code == 200, r.text
    po = r.json()
    state = {"po_id": po["id"], "po_number": po["po_number"], "m0": m0["id"], "m0_name": m0["name"], "m1": m1["id"], "m1_name": m1["name"],
             "snap": snap, "counters": counters, "existing_pos": existing}
    json.dump(state, open(STATE, "w"))
    print(json.dumps({k: state[k] for k in ("po_id", "po_number", "m0_name", "m1_name")}), snap)


def status():
    st = json.load(open(STATE))
    po = db.purchase_orders.find_one({"id": st["po_id"]}, {"_id": 0, "purchase_proof_data": 0, "arrival_proof_data": 0})
    print("PO:", json.dumps(po, default=str)[:1500])
    for mid in (st["m0"], st["m1"]):
        m = db.materials.find_one({"id": mid}, {"_id": 0, "stock": 1, "pack_price": 1, "name": 1})
        print("MAT", m, "snap", st["snap"][mid])
    print("TX", list(db.inventory_tx.find({"purchase_order_id": st["po_id"]}, {"_id": 0, "qty": 1, "material_name": 1, "cost": 1})))


def cleanup():
    st = json.load(open(STATE))
    new_pos = [p["id"] for p in db.purchase_orders.find({"id": {"$nin": st["existing_pos"]}}, {"id": 1})]
    for po_id in new_pos:
        db.inventory_tx.delete_many({"purchase_order_id": po_id})
        db.notifications.delete_many({"ref_id": po_id})
        db.po_share_audit.delete_many({"po_id": po_id})
        db.purchase_orders.delete_one({"id": po_id})
    for mid, s in st["snap"].items():
        db.materials.update_one({"id": mid}, {"$set": s})
    for c in db.counters.find({"key": {"$regex": "^purchase-order:"}}):
        if c["key"] in st["counters"]:
            db.counters.update_one({"key": c["key"]}, {"$set": {"value": st["counters"][c["key"]]}})
        else:
            db.counters.delete_one({"key": c["key"]})
    print("cleaned POs:", new_pos)


{"setup": setup, "status": status, "cleanup": cleanup}[sys.argv[1]]()
