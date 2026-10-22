# Utility: print document counts for all collections (baseline check before/after QA)
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
for c in sorted(db.list_collection_names()):
    print(c, db[c].count_documents({}))
print("users:", [(u["username"], u["role"]) for u in db.users.find({}, {"username": 1, "role": 1})])
