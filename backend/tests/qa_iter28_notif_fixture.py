# Iter28: temporary notification fixtures for owner (TEST_ ids) - usage: python qa_iter28_notif_fixture.py seed|clean
import sys, os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
owner = db.users.find_one({"username": "baa"}) or db.users.find_one({"role": "owner"})
if sys.argv[1] == "seed":
    base = datetime.now(timezone.utc)
    types = [("purchase_order", "PO baru · TEST Gula", "QA meminta 5 kg"),
             ("deposit", "Setoran · TEST Rider", "Rp 100.000"),
             ("order", "Pesanan Barang · TEST Cust", "2 item"),
             ("withdrawal", "Insentif · TEST Rider", "Rp 50.000"),
             ("broadcast", "Info dari Owner", "TEST pesan broadcast baris 1\nBaris 2 dengan teks yang panjang sekali untuk menguji wrapping pada layar mobile tanpa overflow horizontal sama sekali ya")]
    for i, (t, title, body) in enumerate(types):
        db.notifications.insert_one({"id": f"TEST_{t}", "for_user": owner["id"], "type": t, "title": title, "body": body,
                                     "ref_id": None, "read": False, "created_at": (base + timedelta(seconds=i)).isoformat()})
    print("seeded", owner["id"])
else:
    print("deleted", db.notifications.delete_many({"id": {"$regex": "^TEST_"}}).deleted_count)
