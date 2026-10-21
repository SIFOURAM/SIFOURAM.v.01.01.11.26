# Iter20: Purchase Orders (approval + notif), Owner Broadcast, Payment Accounts/QRIS, Notifications isolation
import os
import uuid
import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
PIN = "246813"
TAG = "TEST_IT20_" + uuid.uuid4().hex[:6]
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def login(i, p):
    r = requests.post(f"{API}/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    r = requests.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": p, "remember": True})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def ctx():
    files_before = [f["id"] for f in mdb.files.find({}, {"_id": 0, "id": 1})]
    o = login("baa", "130994")
    c = {"owner": o, "users": {}, "pos": [], "accts": []}
    for role in ["admin", "barteam", "rider"]:
        un = f"qa20_{role}_{uuid.uuid4().hex[:4]}"
        r = requests.post(f"{API}/users", headers=o, json={"name": f"{TAG} {role}", "username": un, "role": role, "pin": PIN, "whatsapp": "081234567890"})
        assert r.status_code == 200, r.text
        c["users"][role] = r.json()
        c[role] = login(un, PIN)
    c["barteam2_un"] = f"qa20_bt2_{uuid.uuid4().hex[:4]}"
    r = requests.post(f"{API}/users", headers=o, json={"name": f"{TAG} bt2", "username": c["barteam2_un"], "role": "barteam", "pin": PIN})
    c["users"]["barteam2"] = r.json()
    c["barteam2"] = login(c["barteam2_un"], PIN)
    mat = mdb.materials.find_one({}, {"_id": 0})
    assert mat, "no materials seeded"
    c["mat"] = mat
    yield c
    ids = [u["id"] for u in c["users"].values()]
    mdb.purchase_orders.delete_many({"$or": [{"requested_by": {"$in": ids}}, {"note": {"$regex": TAG}}]})
    mdb.notifications.delete_many({"$or": [{"for_user": {"$in": ids}}, {"body": {"$regex": TAG}}, {"ref_id": {"$in": c["pos"]}}]})
    mdb.payment_accounts.delete_many({"name": {"$regex": "^TEST_IT20"}})
    mdb.files.delete_many({"id": {"$nin": files_before}, "folder": "payment_accounts"})
    mdb.users.delete_many({"id": {"$in": ids}})
    mdb.login_attempts.delete_many({"identifier": {"$regex": "qa20_"}})


# --- Purchase Orders ---
class TestPurchaseOrders:
    def test_barteam_create_po_and_owner_notified(self, ctx):
        r = requests.post(f"{API}/purchase-orders", headers=ctx["barteam"], json={"material_id": ctx["mat"]["id"], "qty": 2.5, "note": f"{TAG} weekend"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "pending" and d["qty"] == 2.5 and d["requested_by"] == ctx["users"]["barteam"]["id"]
        assert "_id" not in d
        ctx["pos"].append(d["id"])
        ctx["po1"] = d["id"]
        n = requests.get(f"{API}/notifications", headers=ctx["owner"]).json()
        assert any(x.get("ref_id") == d["id"] and x["type"] == "purchase_order" for x in n)

    def test_po_validation(self, ctx):
        r = requests.post(f"{API}/purchase-orders", headers=ctx["barteam"], json={"material_id": ctx["mat"]["id"], "qty": 0})
        assert r.status_code == 400
        r = requests.post(f"{API}/purchase-orders", headers=ctx["barteam"], json={"material_id": "nope", "qty": 1})
        assert r.status_code == 404
        r = requests.post(f"{API}/purchase-orders", headers=ctx["rider"], json={"material_id": ctx["mat"]["id"], "qty": 1})
        assert r.status_code == 403

    def test_list_scoping(self, ctx):
        own = requests.get(f"{API}/purchase-orders", headers=ctx["barteam"]).json()
        assert any(p["id"] == ctx["po1"] for p in own)
        assert all(p["requested_by"] == ctx["users"]["barteam"]["id"] for p in own)
        other = requests.get(f"{API}/purchase-orders", headers=ctx["barteam2"]).json()
        assert not any(p["id"] == ctx["po1"] for p in other)
        for role in ["owner", "admin"]:
            assert any(p["id"] == ctx["po1"] for p in requests.get(f"{API}/purchase-orders", headers=ctx[role]).json())
        assert requests.get(f"{API}/purchase-orders", headers=ctx["rider"]).status_code == 403

    def test_barteam_cannot_decide(self, ctx):
        r = requests.post(f"{API}/purchase-orders/{ctx['po1']}/approve", headers=ctx["barteam"], json={"note": ""})
        assert r.status_code == 403

    def test_invalid_decision(self, ctx):
        r = requests.post(f"{API}/purchase-orders/{ctx['po1']}/maybe", headers=ctx["owner"], json={"note": ""})
        assert r.status_code == 400
        r = requests.post(f"{API}/purchase-orders/nope/approve", headers=ctx["owner"], json={"note": ""})
        assert r.status_code == 404

    def test_admin_approve_notifies_requester(self, ctx):
        r = requests.post(f"{API}/purchase-orders/{ctx['po1']}/approve", headers=ctx["admin"], json={"note": ""})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "approved" and d["approved_by"] == f"{TAG} admin" and d["approved_at"]
        n = requests.get(f"{API}/notifications", headers=ctx["barteam"]).json()
        assert any(x.get("ref_id") == ctx["po1"] and "approved" in x["title"] for x in n)
        # second decision does not flip status
        r2 = requests.post(f"{API}/purchase-orders/{ctx['po1']}/reject", headers=ctx["owner"], json={"note": ""})
        assert r2.status_code == 200 and r2.json()["status"] == "approved"

    def test_owner_reject(self, ctx):
        r = requests.post(f"{API}/purchase-orders", headers=ctx["barteam"], json={"material_id": ctx["mat"]["id"], "qty": 1, "note": TAG})
        pid = r.json()["id"]
        ctx["pos"].append(pid)
        r = requests.post(f"{API}/purchase-orders/{pid}/reject", headers=ctx["owner"], json={"note": f"{TAG} stok cukup"})
        assert r.status_code == 200 and r.json()["status"] == "rejected" and r.json()["decision_note"] == f"{TAG} stok cukup"

    def test_admin_notified_of_new_po(self, ctx):
        # requirement: Owner/Admin approval with notification -> admin should also be notified
        n = requests.get(f"{API}/notifications", headers=ctx["admin"]).json()
        assert any(x.get("ref_id") == ctx["po1"] and x["title"].startswith("PO baru") for x in n), "Admin receives no notification for new PO"


# --- Notifications isolation ---
class TestNotifications:
    def test_no_leak(self, ctx):
        for role in ["barteam2", "rider", "admin"]:
            n = requests.get(f"{API}/notifications", headers=ctx[role]).json()
            uid_ = ctx["users"][role]["id"]
            assert all(x.get("for_user") == uid_ for x in n), f"{role} sees foreign notifications"
        assert requests.get(f"{API}/notifications").status_code in (401, 403)


# --- Broadcast ---
class TestBroadcast:
    def test_non_owner_forbidden(self, ctx):
        for role in ["admin", "barteam", "rider"]:
            assert requests.post(f"{API}/broadcast", headers=ctx[role], json={"roles": ["rider"], "message": "x"}).status_code == 403

    def test_validation(self, ctx):
        assert requests.post(f"{API}/broadcast", headers=ctx["owner"], json={"roles": [], "message": "hi"}).status_code == 400
        assert requests.post(f"{API}/broadcast", headers=ctx["owner"], json={"roles": ["bogus"], "message": "hi"}).status_code == 400
        assert requests.post(f"{API}/broadcast", headers=ctx["owner"], json={"roles": ["rider"], "message": "   "}).status_code == 400

    def test_broadcast_creates_notifications(self, ctx):
        msg = f"{TAG} broadcast hello"
        r = requests.post(f"{API}/broadcast", headers=ctx["owner"], json={"roles": ["rider", "barteam"], "message": msg})
        assert r.status_code == 200, r.text
        rec = r.json()["recipients"]
        names = [x["name"] for x in rec]
        assert f"{TAG} rider" in names and f"{TAG} barteam" in names and f"{TAG} admin" not in names
        assert any(x["whatsapp"] == "081234567890" for x in rec)
        assert set(rec[0].keys()) == {"name", "whatsapp"}
        for role in ["rider", "barteam"]:
            n = requests.get(f"{API}/notifications", headers=ctx[role]).json()
            assert any(x["type"] == "broadcast" and x["body"] == msg for x in n)
        n = requests.get(f"{API}/notifications", headers=ctx["admin"]).json()
        assert not any(x["body"] == msg for x in n)


# --- Payment accounts ---
class TestPaymentAccounts:
    def test_non_owner_forbidden(self, ctx):
        body = {"name": "TEST_IT20 x", "bank_name": "B", "account_number": "1", "account_holder": "H"}
        for role in ["admin", "barteam", "rider"]:
            assert requests.post(f"{API}/payment-accounts", headers=ctx[role], json=body).status_code == 403
            assert requests.get(f"{API}/payment-accounts", headers=ctx[role]).status_code == 403

    def test_invalid_qris(self, ctx):
        body = {"name": "TEST_IT20 bad", "bank_name": "B", "account_number": "1", "account_holder": "H", "qris_photo": "data:text/plain;base64,aGk="}
        assert requests.post(f"{API}/payment-accounts", headers=ctx["owner"], json=body).status_code == 400

    def test_create_and_public(self, ctx):
        body = {"name": "TEST_IT20 QRIS", "bank_name": "BCA", "account_number": "9988776655", "account_holder": "QA Holder", "active": True, "qris_photo": PNG}
        r = requests.post(f"{API}/payment-accounts", headers=ctx["owner"], json=body)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["qris_photo"] and (d["qris_photo"].startswith("/api/files/") or d["qris_photo"].startswith("data:image"))
        ctx["acct"] = d
        lst = requests.get(f"{API}/payment-accounts", headers=ctx["owner"]).json()
        assert any(a["id"] == d["id"] and a["account_number"] == "9988776655" for a in lst)
        inactive = {**body, "name": "TEST_IT20 inactive", "active": False}
        ina = requests.post(f"{API}/payment-accounts", headers=ctx["owner"], json=inactive).json()
        noq = requests.post(f"{API}/payment-accounts", headers=ctx["owner"], json={**body, "name": "TEST_IT20 noqris", "qris_photo": None}).json()
        for role in ["rider", "barteam", "admin", "owner"]:
            pub = requests.get(f"{API}/payment-accounts/public", headers=ctx[role])
            assert pub.status_code == 200
            p = pub.json()
            mine = [a for a in p if a["id"] == d["id"]]
            assert mine and set(mine[0].keys()) <= {"id", "name", "bank_name", "qris_photo"}
            assert not any(a["id"] in (ina["id"], noq["id"]) for a in p)
        assert requests.get(f"{API}/payment-accounts/public").status_code in (401, 403)
        if d["qris_photo"].startswith("/api/files/"):
            img = requests.get(os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + d["qris_photo"])
            assert img.status_code == 200 and img.headers["content-type"].startswith("image/")
