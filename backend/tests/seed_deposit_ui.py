# Temporary UI seed for Setoran tests: python seed_deposit_ui.py seed|clean  (hard-deletes everything on clean)
import sys
import uuid
import importlib.util

spec = importlib.util.spec_from_file_location("t", "/app/backend/tests/test_deposit_eod_server_totals.py")
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
t.RIDER_ID = "TEST_rider_ui"
db, R, D = t.db, t.RIDER_ID, t.DATE

t.cleanup()
if sys.argv[1] == "seed":
    db.users.insert_one({"id": R, "name": "TEST_Rider UI", "username": R, "role": "rider", "active": True, "created_at": "2030-01-01"})
    db.rider_stock.insert_one({"id": uuid.uuid4().hex, "rider_id": R, "date": D, "items": {t.AMERICANO: 10, t.KOPSU: 5, t.CREAMY: 4}, "verified_at": "2030-01-15T00:00:00"})
    db.sales.insert_many([
        {"id": uuid.uuid4().hex, "rider_id": R, "date": D, "total": 16000, "payment_method": "cash", "payment_parts": [],
         "items": [{"menu_id": t.AMERICANO, "name": "SI AMERICANO", "qty": 2, "subtotal": 16000}]},
        {"id": uuid.uuid4().hex, "rider_id": R, "date": D, "total": 10000, "payment_method": "qris", "payment_parts": [],
         "items": [{"menu_id": t.KOPSU, "name": "SI KOPSU AREN", "qty": 1, "subtotal": 10000}]},
        {"id": uuid.uuid4().hex, "rider_id": R, "date": D, "total": 45000, "payment_method": "split",
         "payment_parts": [{"method": "cash", "amount": 20000}, {"method": "qris", "amount": 25000}],
         "items": [{"menu_id": "bundle-1", "bundle": 1, "name": "BUNDLING 1", "qty": 1, "subtotal": 45000, "components": {t.AMERICANO: 2, t.CREAMY: 2}}]},
    ])
    db.eod.insert_one({"rider_id": R, "date": D, "closed_by": "TEST", "time": "20:00"})
    print("seeded", R)
else:
    print("cleaned", db.users.count_documents({"id": R}))
