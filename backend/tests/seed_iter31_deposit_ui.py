# Temporary UI seed for Setoran iteration 31: python seed_iter31_deposit_ui.py seed|clean (hard deletes on clean)
import sys
import uuid
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
R, D = "TEST_rider_ui31", "2030-01-15"
AMERICANO = "6cc0ca7c-b6f4-4b0c-b6e6-c21707d4e4e4"
KOPSU = "c9750dec-4968-4cd2-be2b-0695eb0bafe7"


def clean():
    dep_ids = [d["id"] for d in db.deposits.find({"rider_id": R})]
    inv_ids = [i["id"] for i in db.invoices.find({"customer_name": {"$regex": "^TEST_"}})]
    db.notifications.delete_many({"ref_id": {"$in": dep_ids + inv_ids}})
    for c in ["deposits", "sales", "eod", "rider_stock", "menu_stock_tx"]:
        db[c].delete_many({"rider_id": R})
    db.invoices.delete_many({"customer_name": {"$regex": "^TEST_"}})
    db.customers.delete_many({"name": {"$regex": "^TEST_"}})
    db.users.delete_many({"id": R})


clean()
if sys.argv[1] == "seed":
    db.users.insert_one({"id": R, "name": "TEST_Rider UI31", "username": R, "role": "rider", "active": True, "created_at": "2030-01-01"})
    db.rider_stock.insert_one({"id": uuid.uuid4().hex, "rider_id": R, "date": D, "items": {AMERICANO: 10, KOPSU: 5}, "verified_at": "2030-01-15T00:00:00"})
    db.sales.insert_one({"id": uuid.uuid4().hex, "rider_id": R, "date": D, "total": 16000, "payment_method": "cash", "payment_parts": [],
                         "items": [{"menu_id": AMERICANO, "name": "SI AMERICANO", "qty": 2, "subtotal": 16000}]})
    db.eod.insert_one({"rider_id": R, "date": D, "closed_by": "TEST", "time": "20:00"})
    print("seeded", R)
else:
    print("cleaned")
