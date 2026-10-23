# Iteration 46: Purchase flow re-test — proof privacy, merge duplicates, price update ordering, receive-once, proof endpoint auth
import base64
import os
from io import BytesIO

import pytest
import requests
from PIL import Image, ImageDraw
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


def _env(path, key):
    for line in open(path):
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')


MONGO = MongoClient(_env("/app/backend/.env", "MONGO_URL"))[_env("/app/backend/.env", "DB_NAME")]
CREATED_POS = []
MATERIAL_SNAPSHOT = {}


def proof_image(color="white"):
    img = Image.new("RGB", (120, 120), color)
    d = ImageDraw.Draw(img)
    for i in range(0, 120, 8):
        d.line([(0, i), (120, 120 - i)], fill=(i * 2, 0, 255 - i * 2), width=3)
    buf = BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def login(identifier, pin):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": identifier, "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    tok = r.json().get("account_token") or r.json().get("token")
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": tok, "pin": pin, "remember": False})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def owner():
    return login("baa", "130994")


@pytest.fixture(scope="module")
def admin():
    return login("dummy_admin", "100002")


@pytest.fixture(scope="module")
def bar():
    return login("dummy_barteam", "100003")


@pytest.fixture(scope="module")
def materials(owner):
    mats = owner.get(f"{BASE_URL}/api/materials").json()
    assert len(mats) >= 2
    for m in mats[:2]:
        doc = MONGO.materials.find_one({"id": m["id"]})
        MATERIAL_SNAPSHOT[m["id"]] = {"stock": doc.get("stock", 0), "pack_price": doc.get("pack_price")}
    return mats[:2]


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    counter_before = {c["key"]: c["value"] for c in MONGO.counters.find({"key": {"$regex": "^purchase-order:"}})}
    yield
    for po_id in CREATED_POS:
        MONGO.inventory_tx.delete_many({"purchase_order_id": po_id})
        MONGO.notifications.delete_many({"ref_id": po_id})
        MONGO.po_share_audit.delete_many({"po_id": po_id})
        MONGO.purchase_orders.delete_one({"id": po_id})
    for mid, snap in MATERIAL_SNAPSHOT.items():
        MONGO.materials.update_one({"id": mid}, {"$set": {"stock": snap["stock"], "pack_price": snap["pack_price"]}})
    for c in MONGO.counters.find({"key": {"$regex": "^purchase-order:"}}):
        if c["key"] in counter_before:
            MONGO.counters.update_one({"key": c["key"]}, {"$set": {"value": counter_before[c["key"]]}})
        else:
            MONGO.counters.delete_one({"key": c["key"]})


def create_po(bar, mat, qty=2):
    r = bar.post(f"{BASE_URL}/api/purchase-orders", json={"items": [{"material_id": mat["id"], "qty": qty, "unit_price": 1000}], "vendor_name": "TEST_vendor", "note": "TEST_QA"})
    assert r.status_code == 200, r.text
    CREATED_POS.append(r.json()["id"])
    return r.json()


class TestPurchaseIter46:
    def test_purchase_response_and_list_exclude_raw_proof(self, owner, admin, bar, materials):
        m = materials[0]
        po = create_po(bar, m)
        r = admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"proof": proof_image(), "items": [{"material_id": m["id"], "qty": 2, "unit_price": 1234}]})
        assert r.status_code == 200, r.text
        assert "purchase_proof_data" not in r.json()
        assert r.json()["status"] == "purchased"
        for s in (owner, admin, bar):
            lst = s.get(f"{BASE_URL}/api/purchase-orders").json()
            assert all("purchase_proof_data" not in o and "arrival_proof_data" not in o for o in lst)
            assert any(o["id"] == po["id"] for o in lst)
        # DB still holds proof
        assert MONGO.purchase_orders.find_one({"id": po["id"]})["purchase_proof_data"].startswith("data:image/png")

    def test_merge_duplicate_rows(self, owner, bar, materials):
        a, b = materials
        po = create_po(bar, a)
        items = [{"material_id": a["id"], "qty": 1, "unit_price": 100},
                 {"material_id": b["id"], "qty": 4, "unit_price": 50},
                 {"material_id": a["id"], "qty": 2.5, "unit_price": 200}]
        r = owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"items": items})
        assert r.status_code == 200, r.text
        pi = {i["material_id"]: i for i in r.json()["purchase_items"]}
        assert len(r.json()["purchase_items"]) == 2
        assert pi[a["id"]]["qty"] == pytest.approx(3.5)
        assert pi[a["id"]]["unit_price"] == 200
        assert pi[a["id"]]["subtotal"] == 700
        assert pi[a["id"]]["material_name"] == a["name"]
        assert pi[b["id"]]["subtotal"] == 200
        # price updated to last revised price
        assert MONGO.materials.find_one({"id": a["id"]})["pack_price"] == 200
        assert MONGO.materials.find_one({"id": b["id"]})["pack_price"] == 50

    def test_price_not_updated_on_failed_transition(self, owner, bar, materials):
        m = materials[1]
        po = create_po(bar, m)
        assert owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"items": [{"material_id": m["id"], "qty": 1, "unit_price": 777}]}).status_code == 200
        price_before = MONGO.materials.find_one({"id": m["id"]})["pack_price"]
        r = owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"items": [{"material_id": m["id"], "qty": 1, "unit_price": 99999}]})
        assert r.status_code == 409
        assert MONGO.materials.find_one({"id": m["id"]})["pack_price"] == price_before
        # invalid proof -> 400 and no price update / no transition
        po2 = create_po(bar, m)
        r = owner.post(f"{BASE_URL}/api/purchase-orders/{po2['id']}/purchase", json={"proof": "data:text/plain;base64,AAAA", "items": [{"material_id": m["id"], "qty": 1, "unit_price": 55555}]})
        assert r.status_code == 400
        assert MONGO.materials.find_one({"id": m["id"]})["pack_price"] == price_before
        assert MONGO.purchase_orders.find_one({"id": po2["id"]})["status"] == "requested"

    def test_barteam_receive_increments_once(self, admin, bar, materials):
        m = materials[0]
        po = create_po(bar, m, qty=2)
        assert admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"proof": proof_image(), "items": [{"material_id": m["id"], "qty": 5, "unit_price": 300}]}).status_code == 200
        stock_before = MONGO.materials.find_one({"id": m["id"]})["stock"]
        r = bar.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/receive", json={"photo": proof_image("red"), "received_note": "TEST"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "arrived"
        assert MONGO.materials.find_one({"id": m["id"]})["stock"] == pytest.approx(stock_before + 5)
        r2 = bar.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/receive", json={"photo": proof_image("red")})
        assert r2.status_code == 409
        assert MONGO.materials.find_one({"id": m["id"]})["stock"] == pytest.approx(stock_before + 5)
        tx = list(MONGO.inventory_tx.find({"purchase_order_id": po["id"]}))
        assert len(tx) == 1 and tx[0]["cost"] == 1500

    def test_receive_response_excludes_raw_purchase_proof(self, admin, bar, materials):
        m = materials[1]
        po = create_po(bar, m)
        admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"proof": proof_image(), "items": [{"material_id": m["id"], "qty": 1, "unit_price": 10}]})
        r = bar.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/receive", json={"photo": proof_image()})
        assert r.status_code == 200
        assert "purchase_proof_data" not in r.json(), "receive response leaks raw purchase_proof_data"

    def test_purchase_proof_endpoint_protected(self, owner, admin, bar, materials):
        m = materials[0]
        po = create_po(bar, m)
        admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"proof": proof_image(), "items": [{"material_id": m["id"], "qty": 1, "unit_price": 10}]})
        url = f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase-proof"
        assert requests.get(url).status_code == 401
        for s in (owner, admin, bar):
            r = s.get(url)
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("image/png")
            assert "no-store" in r.headers.get("cache-control", "")
        rider = login("dummy_rider", "100004")
        assert rider.get(url).status_code == 403
        # PO without proof -> 404
        po2 = create_po(bar, m)
        assert owner.get(f"{BASE_URL}/api/purchase-orders/{po2['id']}/purchase-proof").status_code == 404

    def test_barteam_cannot_view_other_users_purchase_proof(self, owner, admin, materials):
        m = materials[0]
        r = owner.post(f"{BASE_URL}/api/purchase-orders", json={"items": [{"material_id": m["id"], "qty": 1, "unit_price": 1}], "note": "TEST_QA"})
        assert r.status_code == 200
        po = r.json(); CREATED_POS.append(po["id"])
        admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"proof": proof_image(), "items": [{"material_id": m["id"], "qty": 1, "unit_price": 1}]})
        bar = login("dummy_barteam", "100003")
        assert bar.get(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase-proof").status_code == 404

    def test_malformed_items_no_500(self, owner, bar, materials):
        po = create_po(bar, materials[0])
        for bad in (["x"], [{"material_id": materials[0]["id"], "qty": "abc", "unit_price": 1}]):
            r = owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"items": bad})
            assert r.status_code in (400, 422), f"malformed {bad} -> {r.status_code}"
