# Iter46 UI QA helper: `setup` creates a TEST_ PO + snapshots materials; `cleanup` restores everything
import json, os, sys, requests
from io import BytesIO
from PIL import Image, ImageDraw
from pymongo import MongoClient

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL")][0]
env = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l)
db = MongoClient(env["MONGO_URL"].strip('"'))[env["DB_NAME"].strip('"')]
STATE = "/tmp/iter46_ui_state.json"


def login(i, p):
    s = requests.Session()
    t = s.post(f"{BASE}/api/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True}).json()
    s.post(f"{BASE}/api/auth/login", json={"account_token": t.get("account_token") or t.get("token"), "pin": p, "remember": False}).raise_for_status()
    return s


if sys.argv[1] == "setup":
    img = Image.new("RGB", (300, 300), "white"); d = ImageDraw.Draw(img)
    for i in range(0, 300, 10): d.line([(0, i), (300, 300 - i)], fill=(i % 255, 0, 255 - i % 255), width=3)
    img.save("/tmp/iter46_proof.png")
    counters = {c["key"]: c["value"] for c in db.counters.find({"key": {"$regex": "^purchase-order:"}}, {"_id": 0})}
    bar = login("dummy_barteam", "100003")
    mats = bar.get(f"{BASE}/api/materials").json()[:2]
    snap = {m["id"]: {k: db.materials.find_one({"id": m["id"]}).get(k) for k in ("stock", "pack_price")} for m in mats}
    po = bar.post(f"{BASE}/api/purchase-orders", json={"items": [{"material_id": mats[0]["id"], "qty": 2, "unit_price": 1000}], "vendor_name": "TEST_vendor_ui", "note": "TEST_QA_UI"}).json()
    json.dump({"po": po["id"], "po_number": po["po_number"], "mats": mats, "snap": snap, "counters": counters}, open(STATE, "w"))
    print(json.dumps({"po": po["id"], "po_number": po["po_number"], "m0": mats[0]["name"], "m1": mats[1]["name"], "snap": snap}))
else:
    st = json.load(open(STATE))
    po = db.purchase_orders.find_one({"id": st["po"]}, {"_id": 0, "purchase_proof_data": 0, "arrival_proof_data": 0})
    print("PO FINAL:", json.dumps({k: po.get(k) for k in ("status", "purchase_items", "purchase_vendor")} if po else None, default=str))
    for mid in st["snap"]:
        m = db.materials.find_one({"id": mid}); print("MAT", m["name"], "stock", m.get("stock"), "price", m.get("pack_price"), "snap", st["snap"][mid])
    print("TX:", list(db.inventory_tx.find({"purchase_order_id": st["po"]}, {"_id": 0, "qty": 1, "cost": 1, "material_name": 1})))
    if sys.argv[1] == "cleanup":
        db.inventory_tx.delete_many({"purchase_order_id": st["po"]}); db.notifications.delete_many({"ref_id": st["po"]})
        db.po_share_audit.delete_many({"po_id": st["po"]}); db.purchase_orders.delete_one({"id": st["po"]})
        for mid, s in st["snap"].items(): db.materials.update_one({"id": mid}, {"$set": s})
        for c in db.counters.find({"key": {"$regex": "^purchase-order:"}}):
            if c["key"] in st["counters"]: db.counters.update_one({"key": c["key"]}, {"$set": {"value": st["counters"][c["key"]]}})
            else: db.counters.delete_one({"key": c["key"]})
        print("cleaned")
