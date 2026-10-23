# Iteration 44: POS QRIS sale regression (owner selling for dummy rider with verified stock); cleans up via Mongo
import os
import asyncio
import uuid
import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
RIDER_ID = "6415a9eb-47d4-4ebd-8d06-4a7e8a0eeb63"
AMERICANO = "6cc0ca7c-b6f4-4b0c-b6e6-c21707d4e4e4"


def _mongo(coro_fn):
    async def run():
        db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        return await coro_fn(db)
    return asyncio.run(run())


@pytest.fixture(scope="module")
def owner():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    tok = r.json().get("account_token") or r.json().get("token")
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": tok, "pin": "130994", "remember": True})
    if r.status_code != 200:
        pytest.skip(f"owner login failed: {r.text}")
    return s


@pytest.fixture
def created(owner):
    ids = []
    yield ids
    if ids:
        async def clean(db):
            for sale in await db.sales.find({"id": {"$in": ids}}, {"_id": 0, "date": 1}).to_list(10):
                await db.counters.update_one({"key": f"sale:{sale['date']}"}, {"$inc": {"value": -1}})
            await db.sales.delete_many({"id": {"$in": ids}})
        _mongo(clean)


def _today(owner):
    st = owner.get(f"{BASE_URL}/api/rider-stock/history", params={"start": "2000-01-01", "end": "2100-01-01", "rider_id": RIDER_ID}).json()
    return st[0]["date"] if st else None


def test_qris_sale_has_zero_change_and_is_idempotent(owner, created):
    date = _today(owner)
    stock = owner.get(f"{BASE_URL}/api/pos/stock", params={"rider_id": RIDER_ID, "date": date}).json()
    item = next(i for i in stock["items"] if i["menu_id"] == AMERICANO)
    if not stock["has_stock"] or item["remaining"] < 1 or stock["closed"] or stock["deposited"]:
        pytest.skip("dummy rider has no sellable verified stock today")
    body = {"rider_id": RIDER_ID, "date": date, "customer_name": "", "customer_phone": "",
            "items": [{"menu_id": AMERICANO, "qty": 1}], "payment_method": "qris", "payment_parts": [],
            "cash_received": 0, "order_type": "takeaway", "table_number": "", "client_id": str(uuid.uuid4())}
    r = owner.post(f"{BASE_URL}/api/sales", json=body)
    assert r.status_code == 200, r.text
    sale = r.json()
    created.append(sale["id"])
    assert sale["payment_method"] == "qris"
    assert sale["payment_parts"] == [{"method": "qris", "amount": 8000}]
    # idempotency by client_id
    r2 = owner.post(f"{BASE_URL}/api/sales", json=body)
    assert r2.json()["id"] == sale["id"]
    # QRIS sale must not report cash change
    assert sale["change"] == 0, f"QRIS sale reports change={sale['change']} (expected 0)"
