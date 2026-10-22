# Temporary UI seed for Reports iteration 32: python seed_iter32_reports_ui.py seed|clean (hard deletes on clean)
import sys
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
RA, RB, D = "TEST_rider_rep32a", "TEST_rider_rep32b", "2030-02-10"
AMERICANO = "6cc0ca7c-b6f4-4b0c-b6e6-c21707d4e4e4"
KOPSU = "c9750dec-4968-4cd2-be2b-0695eb0bafe7"
CREAMY = "6c5553d9-8c31-4a73-8348-c3e4b1c819f5"
MATCHA = "d108663a-f470-44aa-88fe-4ff80c7e46e8"


def clean():
    for c in ["deposits", "sales", "eod", "rider_stock", "menu_stock_tx"]:
        db[c].delete_many({"rider_id": {"$in": [RA, RB]}})
    db.users.delete_many({"id": {"$in": [RA, RB]}})


clean()
if sys.argv[1] == "seed":
    db.users.insert_many([
        {"id": RA, "name": "TEST_Rider RepA", "username": RA, "role": "rider", "active": True, "created_at": "2030-01-01"},
        {"id": RB, "name": "TEST_Rider RepB", "username": RB, "role": "rider", "active": True, "created_at": "2030-01-01"},
    ])
    db.sales.insert_many([
        {"id": "TEST_rs1", "rider_id": RA, "rider_name": "TEST_Rider RepA", "receipt_no": "TEST-R1", "date": D, "time": "08:15", "total": 16000, "cups": 2,
         "payment_method": "cash", "payment_parts": [], "order_type": "takeaway",
         "items": [{"menu_id": AMERICANO, "name": "SI AMERICANO", "qty": 2, "price": 8000, "subtotal": 16000}]},
        {"id": "TEST_rs2", "rider_id": RA, "rider_name": "TEST_Rider RepA", "receipt_no": "TEST-R2", "date": D, "time": "09:30", "total": 22000, "cups": 2,
         "payment_method": "qris", "payment_parts": [], "order_type": "dine_in",
         "items": [{"menu_id": KOPSU, "name": "SI KOPSU AREN", "qty": 1, "price": 10000, "subtotal": 10000},
                   {"menu_id": CREAMY, "name": "SI CREAMY LATTE", "qty": 1, "price": 12000, "subtotal": 12000}]},
        {"id": "TEST_rs3", "rider_id": RB, "rider_name": "TEST_Rider RepB", "receipt_no": "TEST-R3", "date": D, "time": "09:45", "total": 45000, "cups": 4,
         "payment_method": "split", "payment_parts": [{"method": "cash", "amount": 20000}, {"method": "qris", "amount": 25000}], "order_type": "online",
         "items": [{"menu_id": None, "bundle": 1, "name": "BUNDLING 1 (4 cups)", "qty": 1, "price": 45000, "subtotal": 45000,
                    "components": {CREAMY: 2, MATCHA: 2}, "component_names": {"SI CREAMY LATTE": 2, "SI MATCHA": 2}}]},
    ])
    print("seeded")
else:
    print("cleaned")
