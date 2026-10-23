# Iteration 45: Purchase workflow (PO -> purchase -> Barang Masuk) + AI safe failure + deposit access
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


def proof_image():
    img = Image.new("RGB", (200, 200), "white")
    d = ImageDraw.Draw(img)
    for i in range(0, 200, 10):
        d.line([(0, i), (200, 200 - i)], fill=(i, 0, 255 - i), width=3)
    d.text((10, 90), "TEST STRUK 12000", fill="black")
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
        MATERIAL_SNAPSHOT[m["id"]] = {"stock": m.get("stock", 0), "pack_price": m.get("pack_price")}
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
    assert r.json()["status"] == "requested"
    return r.json()


class TestPurchaseFlow:
    def test_purchase_requires_owner_admin(self, bar, materials):
        po = create_po(bar, materials[0])
        r = bar.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={})
        assert r.status_code == 403

    def test_approved_po_purchase_then_receive_once(self, owner, admin, bar, materials):
        m = materials[0]
        po = create_po(bar, m, qty=2)
        assert admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/action/review", json={"note": ""}).status_code == 200
        assert owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/action/approve", json={"note": ""}).status_code == 200
        stock_before = MONGO.materials.find_one({"id": m["id"]})["stock"]
        items = [{"material_id": m["id"], "material_name": m["name"], "unit": m["unit"], "qty": 3, "unit_price": 1500}]
        r = admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"vendor_name": "TEST_Toko", "purchase_date": "2026-01-10", "note": "TEST_note", "proof": proof_image(), "items": items})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "purchased"
        assert d["purchase_vendor"] == "TEST_Toko"
        assert d["purchase_date"] == "2026-01-10"
        assert d["purchase_items"][0]["qty"] == 3
        assert d["purchase_proof_data"].startswith("data:image/png")
        # duplicate purchase -> 409
        assert admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"items": items}).status_code == 409
        # receive by bar team
        r = bar.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/receive", json={"photo": proof_image(), "received_note": "TEST"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "arrived"
        stock_after = MONGO.materials.find_one({"id": m["id"]})["stock"]
        assert stock_after == pytest.approx(stock_before + 3)  # purchase_items qty, not PO qty 2
        tx = list(MONGO.inventory_tx.find({"purchase_order_id": po["id"]}))
        assert len(tx) == 1 and tx[0]["cost"] == 4500
        r2 = bar.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/receive", json={"photo": proof_image()})
        assert r2.status_code == 409
        assert MONGO.materials.find_one({"id": m["id"]})["stock"] == pytest.approx(stock_after)

    @pytest.mark.parametrize("stage", ["requested", "reviewed"])
    def test_non_approved_po_becomes_purchased(self, owner, admin, bar, materials, stage):
        po = create_po(bar, materials[1], qty=1)
        if stage == "reviewed":
            assert admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/action/review", json={"note": ""}).status_code == 200
        r = owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"vendor_name": "TEST_V", "items": [{"material_id": materials[1]["id"], "qty": 1, "unit_price": 500}]})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "purchased", f"status stayed {r.json()['status']} for {stage} PO"

    def test_shipped_po_becomes_purchased(self, owner, admin, bar, materials):
        po = create_po(bar, materials[1], qty=1)
        admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/action/review", json={"note": ""})
        owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/action/approve", json={"note": ""})
        assert admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/action/ship", json={"note": ""}).status_code == 200
        r = owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"items": [{"material_id": materials[1]["id"], "qty": 1, "unit_price": 500}]})
        assert r.status_code == 200
        assert r.json()["status"] == "purchased", f"status stayed {r.json()['status']}"

    def test_invalid_items_rejected(self, owner, bar, materials):
        po = create_po(bar, materials[0])
        r = owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"items": [{"material_id": materials[0]["id"], "qty": 0, "unit_price": 1}]})
        assert r.status_code == 400

    def test_unknown_material_rejected(self, owner, bar, materials):
        po = create_po(bar, materials[0])
        r = owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"items": [{"material_id": "TEST_nonexistent", "qty": 1, "unit_price": 1}]})
        assert r.status_code in (400, 404), f"got {r.status_code}"

    def test_duplicate_material_in_purchase_items_receivable(self, owner, admin, bar, materials):
        # UI 'Tambah Bahan' can add a duplicate of materials[0]
        m = materials[0]
        po = create_po(bar, m)
        admin.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/action/review", json={"note": ""})
        owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/action/approve", json={"note": ""})
        items = [{"material_id": m["id"], "qty": 1, "unit_price": 100}, {"material_id": m["id"], "qty": 1, "unit_price": 100}]
        r = owner.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/purchase", json={"items": items})
        if r.status_code == 400:
            return  # rejected up-front is acceptable
        assert r.json()["status"] == "purchased"
        rr = bar.post(f"{BASE_URL}/api/purchase-orders/{po['id']}/receive", json={"photo": proof_image()})
        assert rr.status_code == 200, f"receive blocked: {rr.status_code} {rr.text}"


class TestAIAndAccess:
    def test_ai_extract_safe_failure(self, owner):
        r = owner.post(f"{BASE_URL}/api/expenses/extract", json={"proof": proof_image()}, timeout=120)
        assert r.status_code in (200, 424), r.text
        if r.status_code == 424:
            assert "manual" in r.json()["detail"].lower()

    def test_admin_deposits_access(self, admin):
        r = admin.get(f"{BASE_URL}/api/deposits", params={"start": "2026-01-01", "end": "2026-01-31"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)
