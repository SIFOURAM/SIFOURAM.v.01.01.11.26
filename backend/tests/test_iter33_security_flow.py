# Iteration 33: cookie-session auth/security hardening, role/session revocation, and full
# Rider stock -> POS -> EOD -> manual Deposit -> Invoice -> Sales report smoke.
# Run: pytest tests/test_iter33_security_flow.py -n 0 -p no:cacheprovider
# All temp data (TEST_ prefixed users, date 2031-03-15) is hard-deleted at teardown; menu stock restored.
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

DATE = "2031-03-15"
AMERICANO = "6cc0ca7c-b6f4-4b0c-b6e6-c21707d4e4e4"  # 8000
CREAMY = "6c5553d9-8c31-4a73-8348-c3e4b1c819f5"  # 12000
MATCHA = "d108663a-f470-44aa-88fe-4ff80c7e46e8"  # 12000
PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
SUFFIX = uuid.uuid4().hex[:6]
RIDER_U = f"test_r33_{SUFFIX}"
REVOKE_U = f"test_v33_{SUFFIX}"
RIDER_PIN, REVOKE_PIN = "246810", "135791"
INV_CUSTOMER = f"TEST_INV33_{SUFFIX}"
STATE = {}
MENU_BASELINE = {m["id"]: m.get("stock", 0) for m in db.menus.find({}, {"_id": 0, "id": 1, "stock": 1})}


def login(identifier, pin, headers=None):
    s = requests.Session()
    if headers:
        s.headers.update(headers)
    r = s.post(f"{API}/auth/identify", json={"identifier": identifier, "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": pin, "remember": True})
    return s, r


def cleanup():
    ids = [u["id"] for u in db.users.find({"username": {"$regex": "^test_(r|v)33_"}}, {"id": 1})]
    dep_ids = [d["id"] for d in db.deposits.find({"rider_id": {"$in": ids}}, {"id": 1})]
    inv_ids = [i["id"] for i in db.invoices.find({"customer_name": {"$regex": "^TEST_INV33_"}}, {"id": 1})]
    db.notifications.delete_many({"ref_id": {"$in": dep_ids + inv_ids}})
    db.invoices.delete_many({"id": {"$in": inv_ids}})
    for c in ("deposits", "sales", "eod", "rider_stock", "menu_stock_tx"):
        db[c].delete_many({"rider_id": {"$in": ids}})
    db.sales.delete_many({"date": DATE})
    db.customers.delete_many({"name": {"$regex": "^TEST_"}})
    db.files.delete_many({"user_id": {"$in": ids}})
    db.sessions.delete_many({"user_id": {"$in": ids}})
    db.audit_logs.delete_many({"user_id": {"$in": ids}})
    db.login_attempts.delete_many({"identifier": {"$regex": "|".join(ids) or "^$"}})
    db.users.delete_many({"id": {"$in": ids}})
    for mid, stock in MENU_BASELINE.items():
        db.menus.update_one({"id": mid}, {"$set": {"stock": stock}})


@pytest.fixture(scope="module", autouse=True)
def setup_module_data():
    cleanup()
    for menu_id, quantity in ((AMERICANO, 20), (CREAMY, 20), (MATCHA, 20)):
        db.menus.update_one({"id": menu_id}, {"$set": {"stock": quantity}})
    yield
    cleanup()


@pytest.fixture(scope="module")
def owner():
    s, r = login("baa", "130994")
    assert r.status_code == 200, r.text
    STATE["owner_login"] = r
    return s


@pytest.fixture(scope="module")
def rider(owner):
    r = owner.post(f"{API}/users", json={"name": "TEST_Rider33", "username": RIDER_U, "role": "rider", "pin": RIDER_PIN, "active": True})
    assert r.status_code == 200, r.text
    STATE["rider_id"] = r.json()["id"]
    s, lr = login(RIDER_U, RIDER_PIN)
    assert lr.status_code == 200, lr.text
    return s


# ---------- Auth / security ----------
class TestAuthSecurity:
    def test_login_returns_user_only_and_secure_cookie(self, owner):
        r = STATE["owner_login"]
        assert set(r.json().keys()) == {"user"}
        assert "pin_hash" not in r.json()["user"] and "password_hash" not in r.json()["user"]
        sc = r.headers.get("set-cookie", "").lower()
        # backend sets SameSite=Lax; preview ingress rewrites to SameSite=None; Partitioned
        assert "si4am_session=" in sc and "httponly" in sc and "secure" in sc and "samesite=" in sc

    def test_me_with_cookie_and_headers(self, owner):
        r = owner.get(f"{API}/auth/me")
        assert r.status_code == 200 and r.json()["username"] == "baa" and r.json()["role"] == "owner"
        h = r.headers
        assert h.get("x-content-type-options") == "nosniff"
        assert h.get("x-frame-options") == "DENY"
        assert h.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "geolocation" in (h.get("permissions-policy") or "")
        assert "no-store" in (h.get("cache-control") or "")

    def test_unauthenticated_401(self):
        assert requests.get(f"{API}/auth/me").status_code == 401

    def test_legacy_token_without_sid_401(self, owner):
        me = owner.get(f"{API}/auth/me").json()
        legacy = jwt.encode({"sub": me["id"], "exp": datetime.now(timezone.utc) + timedelta(hours=1), "type": "access"}, os.environ["JWT_SECRET"], algorithm="HS256")
        assert requests.get(f"{API}/auth/me", cookies={"si4am_session": legacy}).status_code == 401
        assert requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {legacy}"}).status_code == 401
        ident = jwt.encode({"sub": me["id"], "exp": datetime.now(timezone.utc) + timedelta(hours=1), "type": "identified"}, os.environ["JWT_SECRET"], algorithm="HS256")
        assert requests.get(f"{API}/auth/me", cookies={"si4am_session": ident}).status_code == 401
        assert requests.get(f"{API}/auth/me", cookies={"si4am_session": "garbage.token.x"}).status_code == 401

    def test_logout_revokes_session(self):
        s, r = login("baa", "130994")
        assert r.status_code == 200
        token = s.cookies.get("si4am_session")
        assert s.get(f"{API}/auth/me").status_code == 200
        assert s.post(f"{API}/auth/logout").status_code == 200
        # replay the captured cookie value after logout
        assert requests.get(f"{API}/auth/me", cookies={"si4am_session": token}).status_code == 401

    def test_owner_cannot_self_demote_or_deactivate(self, owner):
        me = owner.get(f"{API}/auth/me").json()
        assert owner.put(f"{API}/users/{me['id']}", json={"role": "admin"}).status_code == 400
        assert owner.put(f"{API}/users/{me['id']}", json={"active": False}).status_code == 400
        assert owner.get(f"{API}/auth/me").json()["role"] == "owner"

    def test_rider_report_forbidden(self, rider):
        r = rider.get(f"{API}/reports/sales", params={"start": DATE, "end": DATE})
        assert r.status_code == 403
        assert rider.get(f"{API}/users").status_code == 403
        assert rider.get(f"{API}/invoices").status_code == 403


# ---------- Role/session revocation ----------
class TestRevocation:
    @pytest.mark.parametrize("change", [{"role": "barteam"}, {"pin": "975310"}, {"password": "NewPass#2031"}, {"active": False}])
    def test_sensitive_update_revokes_prior_session(self, owner, change):
        if "revoke_id" not in STATE:
            r = owner.post(f"{API}/users", json={"name": "TEST_Revoke33", "username": REVOKE_U, "role": "rider", "pin": REVOKE_PIN, "active": True})
            assert r.status_code == 200, r.text
            STATE["revoke_id"] = r.json()["id"]
        uid_ = STATE["revoke_id"]
        # reset to known state (also revokes) then log in fresh
        owner.put(f"{API}/users/{uid_}", json={"role": "rider", "active": True, "pin": REVOKE_PIN})
        s, lr = login(REVOKE_U, REVOKE_PIN)
        assert lr.status_code == 200, lr.text
        assert s.get(f"{API}/auth/me").status_code == 200
        assert owner.put(f"{API}/users/{uid_}", json=change).status_code == 200
        assert s.get(f"{API}/auth/me").status_code == 401

    def test_non_sensitive_update_keeps_session(self, owner, rider):
        assert owner.put(f"{API}/users/{STATE['rider_id']}", json={"name": "TEST_Rider33"}).status_code == 200
        assert rider.get(f"{API}/auth/me").status_code == 200


# ---------- Core functional smoke ----------
class TestCoreFlow:
    def test_01_stock_handoff_pending_blocks_sale(self, owner, rider):
        rid = STATE["rider_id"]
        r = owner.post(f"{API}/rider-stock", json={"rider_id": rid, "date": DATE, "items": {AMERICANO: 5, CREAMY: 6, MATCHA: 4}, "photo": PHOTO})
        assert r.status_code == 200, r.text
        STATE["stock_id"] = r.json()["id"]
        assert r.json()["verified_at"] is None and r.json()["total"] == 15
        st = rider.get(f"{API}/pos/stock", params={"rider_id": rid, "date": DATE}).json()
        assert st["has_stock"] is False and st["pending_stock"] is True
        r = rider.post(f"{API}/sales", json={"rider_id": rid, "date": DATE, "items": [{"menu_id": AMERICANO, "qty": 1}], "payment_method": "cash", "cash_received": 8000, "order_type": "takeaway"})
        assert r.status_code == 400

    def test_02_rider_verifies(self, owner, rider):
        assert owner.post(f"{API}/rider-stock/{STATE['stock_id']}/verify", json={"photo": PHOTO}).status_code == 403
        r = rider.post(f"{API}/rider-stock/{STATE['stock_id']}/verify", json={"photo": PHOTO})
        assert r.status_code == 200 and r.json()["verified_at"]
        st = rider.get(f"{API}/pos/stock", params={"rider_id": STATE["rider_id"], "date": DATE}).json()
        assert st["has_stock"] is True

    def test_03_sales_cash_qris_split(self, rider):
        rid = STATE["rider_id"]
        base = {"rider_id": rid, "date": DATE, "customer_name": "TEST_Cust33"}
        r1 = rider.post(f"{API}/sales", json={**base, "items": [{"menu_id": AMERICANO, "qty": 2}], "payment_method": "cash", "cash_received": 20000, "order_type": "takeaway"})
        assert r1.status_code == 200, r1.text
        assert r1.json()["total"] == 16000 and r1.json()["change"] == 4000
        r2 = rider.post(f"{API}/sales", json={**base, "items": [{"menu_id": CREAMY, "qty": 1}], "payment_method": "qris", "order_type": "dine_in", "table_number": "3"})
        assert r2.status_code == 200, r2.text
        r3 = rider.post(f"{API}/sales", json={**base, "items": [{"bundle": 1, "qty": 1, "components": {CREAMY: 2, MATCHA: 2}}],
                                              "payment_parts": [{"method": "cash", "amount": 20000}, {"method": "qris", "amount": 25000}], "cash_received": 20000, "order_type": "online"})
        assert r3.status_code == 200, r3.text
        assert r3.json()["payment_method"] == "split" and r3.json()["total"] == 45000
        STATE["sale_ids"] = [r1.json()["id"], r2.json()["id"], r3.json()["id"]]

    def test_04_sale_validation(self, rider):
        rid = STATE["rider_id"]
        bad_split = rider.post(f"{API}/sales", json={"rider_id": rid, "date": DATE, "items": [{"menu_id": AMERICANO, "qty": 1}],
                                                     "payment_parts": [{"method": "cash", "amount": 1000}, {"method": "qris", "amount": 1000}], "order_type": "takeaway"})
        assert bad_split.status_code == 400
        over = rider.post(f"{API}/sales", json={"rider_id": rid, "date": DATE, "items": [{"menu_id": MATCHA, "qty": 9}], "payment_method": "qris", "order_type": "takeaway"})
        assert over.status_code == 400

    def test_05_negative_qty_sale_rejected(self, rider):
        r = rider.post(f"{API}/sales", json={"rider_id": STATE["rider_id"], "date": DATE, "items": [{"menu_id": AMERICANO, "qty": -1}], "payment_method": "cash", "cash_received": 0, "order_type": "takeaway"})
        if r.status_code == 200:
            db.sales.delete_one({"id": r.json()["id"]})
        assert r.status_code in (400, 422), f"negative qty sale accepted: {r.text[:200]}"

    def test_06_deposit_requires_eod(self, owner):
        r = owner.post(f"{API}/deposits", json={"rider_id": STATE["rider_id"], "date": DATE, "rows": []})
        assert r.status_code == 400 and "EOD" in r.text

    def test_07_eod_close_and_blocks_sales(self, rider):
        rid = STATE["rider_id"]
        r = rider.post(f"{API}/sales/eod/close", json={"rider_id": rid, "date": DATE})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["closed"] is True and d["transactions"] == 3 and d["total_cups"] == 7
        assert d["total_cash"] == 36000 and d["total_qris"] == 37000
        r = rider.post(f"{API}/sales", json={"rider_id": rid, "date": DATE, "items": [{"menu_id": AMERICANO, "qty": 1}], "payment_method": "qris", "order_type": "takeaway"})
        assert r.status_code == 400

    def test_08_deposit_rejects_over_stock(self, owner):
        r = owner.post(f"{API}/deposits", json={"rider_id": STATE["rider_id"], "date": DATE, "rows": [{"menu_id": AMERICANO, "stock": 5, "cash": 4, "remaining": 2}]})
        assert r.status_code == 400
        assert db.deposits.count_documents({"rider_id": STATE["rider_id"]}) == 0

    def test_09_manual_deposit_accounting(self, owner):
        rows = [
            {"menu_id": AMERICANO, "stock": 5, "cash": 2, "qris": 0, "remaining": 2, "wastage": 1},
            {"menu_id": CREAMY, "stock": 6, "cash": 1, "qris": 2, "remaining": 2, "wastage": 0},
            {"menu_id": MATCHA, "stock": 4, "cash": 1, "qris": 1, "remaining": 2, "wastage": 0},
        ]
        r = owner.post(f"{API}/deposits", json={"rider_id": STATE["rider_id"], "date": DATE, "rows": rows})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_cups"] == 7 and d["total_cash"] == 16000 + 12000 + 12000 and d["total_qris"] == 24000 + 12000
        assert d["minus"] == 12000 and d["total_wastage"] == 1
        creamy = next(x for x in d["rows"] if x["menu_id"] == CREAMY)
        assert creamy["diff"] == 1 and creamy["total_sold"] == 3
        got = owner.get(f"{API}/deposits", params={"start": DATE, "end": DATE, "rider_id": STATE["rider_id"]}).json()
        assert len(got) == 1 and got[0]["minus"] == 12000
        st = owner.get(f"{API}/pos/stock", params={"rider_id": STATE["rider_id"], "date": DATE}).json()
        assert st["deposited"] is True

    def test_10_invoice_create_and_pay(self, owner):
        r = owner.post(f"{API}/invoices", json={"customer_name": INV_CUSTOMER, "customer_phone": "0811", "date": DATE,
                                                "rows": [{"menu_id": AMERICANO, "qty": 10}, {"menu_id": CREAMY, "qty": 5, "price": 11000}],
                                                "discount": 5000, "down_payment": 50000, "payment_method": "cash"})
        assert r.status_code == 200, r.text
        inv = r.json()
        assert inv["subtotal"] == 135000 and inv["total"] == 130000 and inv["remaining"] == 80000 and inv["status"] == "unpaid"
        p = owner.post(f"{API}/invoices/{inv['id']}/pay", json={"amount": 80000, "method": "qris"})
        assert p.status_code == 200 and p.json()["status"] == "paid" and p.json()["remaining"] == 0

    def test_11_invoice_rejects_negative_values(self, owner):
        r = owner.post(f"{API}/invoices", json={"customer_name": INV_CUSTOMER, "customer_phone": "0811", "date": DATE,
                                                "rows": [{"menu_id": AMERICANO, "qty": 1, "price": -8000}], "discount": -1000, "down_payment": 0})
        assert r.status_code in (400, 422), f"negative invoice accepted: {r.text[:150]}"

    def test_12_sales_report_accuracy(self, owner):
        rid = STATE["rider_id"]
        def rep(**p):
            r = owner.get(f"{API}/reports/sales", params={"start": DATE, "end": DATE, "rider_id": rid, **p})
            assert r.status_code == 200, r.text
            return r.json()
        d = rep()
        assert d["transactions"] == 3 and d["revenue"] == 73000 and d["total_cups"] == 7
        assert {t["id"] for t in d["transaction_rows"]} == set(STATE["sale_ids"])
        assert all({"sale_kind", "order_type", "cash", "qris"} <= set(t) for t in d["transaction_rows"])
        assert rep(payment_method="cash")["revenue"] == 36000
        assert rep(payment_method="qris")["revenue"] == 37000
        assert rep(sale_kind="bundling")["revenue"] == 45000
        assert rep(sale_kind="regular")["revenue"] == 28000
        assert rep(service_type="dine_in")["transactions"] == 1
        prods = {p["name"]: p for p in d["products"]}
        assert prods["SI CREAMY LATTE"]["qty"] == 3 and prods["SI MATCHA"]["qty"] == 2
        assert owner.get(f"{API}/reports/sales", params={"start": DATE, "end": "2031-03-01"}).status_code == 400
        assert owner.get(f"{API}/reports/operations", params={"kind": "wastage", "start": DATE, "end": DATE}).status_code == 200


# ---------- Audit + rate limits (run last) ----------
class TestAuditAndRateLimit:
    def test_audit_has_no_secrets(self):
        bad = []
        for row in db.audit_logs.find({}, {"_id": 0}):
            blob = str(row)
            for secret in ("130994", RIDER_PIN, REVOKE_PIN, "eyJ", "pin_hash", "password_hash", "$2b$"):
                if secret in blob:
                    bad.append((secret, row.get("action")))
        assert not bad, bad
        assert db.audit_logs.count_documents({"action": "auth.login"}) > 0

    def test_identify_rate_limit_429(self):
        codes = []
        for _ in range(15):
            codes.append(requests.post(f"{API}/auth/identify", json={"identifier": f"nouser_{SUFFIX}", "terms_accepted": True, "privacy_accepted": True}).status_code)
        assert 429 in codes, codes

    def test_rate_limit_not_bypassable_via_x_forwarded_for(self):
        # bucket is already exhausted by previous test; a spoofed XFF should not reset it
        r = requests.post(f"{API}/auth/identify", headers={"X-Forwarded-For": f"10.9.{int(time.time()) % 250}.7"},
                          json={"identifier": f"nouser_{SUFFIX}", "terms_accepted": True, "privacy_accepted": True})
        assert r.status_code == 429, f"spoofed X-Forwarded-For bypassed rate limit: {r.status_code}"
