# Temporary UI fixtures for iteration 33 (rider + verified stock + 3 sales + EOD for today WIB).
# Usage: python ui_seed_iter33.py seed | clean
import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
RID = "TEST_ui33_rider"
DATE = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
AM, CR, MA = "6cc0ca7c-b6f4-4b0c-b6e6-c21707d4e4e4", "6c5553d9-8c31-4a73-8348-c3e4b1c819f5", "d108663a-f470-44aa-88fe-4ff80c7e46e8"


def clean():
    dep = [d["id"] for d in db.deposits.find({"rider_id": RID})]
    db.notifications.delete_many({"ref_id": {"$in": dep}})
    ids = [RID, RID + "2"]
    dep += [d["id"] for d in db.deposits.find({"rider_id": {"$in": ids}})]
    db.notifications.delete_many({"ref_id": {"$in": dep}})
    for c in ("deposits", "sales", "eod", "rider_stock", "menu_stock_tx", "attendance"):
        db[c].delete_many({"rider_id": {"$in": ids}})
    db.users.delete_many({"id": {"$in": ids}})
    db.sessions.delete_many({"user_id": {"$in": ids}})
    db.customers.delete_many({"name": {"$regex": "^TEST_"}})
    inv = [i["id"] for i in db.invoices.find({"customer_name": {"$regex": "^TEST_"}})]
    db.notifications.delete_many({"ref_id": {"$in": inv}})
    db.invoices.delete_many({"id": {"$in": inv}})


def seed():
    clean()
    db.users.insert_one({"id": RID, "name": "TEST_UI Rider", "username": "test_ui33_rider", "role": "rider", "active": True, "created_at": "2030-01-01"})
    db.rider_stock.insert_one({"id": "TEST_ui33_stock", "rider_id": RID, "rider_name": "TEST_UI Rider", "date": DATE, "items": {AM: 5, CR: 6, MA: 4},
                               "total": 15, "verified_at": "2030-01-01T00:00:00+00:00", "pic_name": "baa", "photo": None})
    base = {"rider_id": RID, "rider_name": "TEST_UI Rider", "date": DATE, "created_at": "2030-01-01"}
    db.sales.insert_many([
        {**base, "id": "TEST_ui33_s1", "receipt_no": "TEST-UI-1", "time": "08:10:00", "total": 16000, "cups": 2, "payment_method": "cash",
         "payment_parts": [{"method": "cash", "amount": 16000}], "order_type": "takeaway",
         "items": [{"menu_id": AM, "name": "SI AMERICANO", "qty": 2, "price": 8000, "subtotal": 16000}]},
        {**base, "id": "TEST_ui33_s2", "receipt_no": "TEST-UI-2", "time": "09:20:00", "total": 12000, "cups": 1, "payment_method": "qris",
         "payment_parts": [{"method": "qris", "amount": 12000}], "order_type": "dine_in", "table_number": "2",
         "items": [{"menu_id": CR, "name": "SI CREAMY LATTE", "qty": 1, "price": 12000, "subtotal": 12000}]},
        {**base, "id": "TEST_ui33_s3", "receipt_no": "TEST-UI-3", "time": "10:30:00", "total": 45000, "cups": 4, "payment_method": "split",
         "payment_parts": [{"method": "cash", "amount": 20000}, {"method": "qris", "amount": 25000}], "order_type": "online",
         "items": [{"menu_id": None, "bundle": 1, "name": "BUNDLING 1 (4 cups)", "qty": 1, "price": 45000, "subtotal": 45000,
                    "components": {CR: 2, MA: 2}, "component_names": {"SI CREAMY LATTE": 2, "SI MATCHA": 2}}]},
    ])
    db.eod.insert_one({"rider_id": RID, "date": DATE, "closed_by": "TEST", "total_cups": 7, "closed_at": "2030-01-01"})
    db.users.insert_one({"id": RID + "2", "name": "TEST_UI Rider2", "username": "test_ui33_rider2", "role": "rider", "active": True, "created_at": "2030-01-01"})
    db.rider_stock.insert_one({"id": "TEST_ui33_stock2", "rider_id": RID + "2", "rider_name": "TEST_UI Rider2", "date": DATE, "items": {AM: 5, CR: 6, MA: 4},
                               "total": 15, "verified_at": "2030-01-01T00:00:00+00:00", "pic_name": "baa", "photo": None})
    print("seeded", DATE)


if __name__ == "__main__":
    seed() if sys.argv[1] == "seed" else clean()
    print("done")
