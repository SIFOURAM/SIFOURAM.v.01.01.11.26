# Iteration 37 UI seed: two Owner coach sessions with distinct messages.
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
owner = db.users.find_one({"username": "baa"})
db.coach_sessions.delete_many({"id": {"$in": ["uiA37", "uiB37"]}})
db.coach_chats.delete_many({"session_id": {"$in": ["uiA37", "uiB37"]}})
db.coach_sessions.insert_many([
    {"id": "uiA37", "user_id": owner["id"], "title": "TEST_Sesi Alpha", "provider": "gpt", "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-02T00:00:00"},
    {"id": "uiB37", "user_id": owner["id"], "title": "TEST_Sesi Beta", "provider": "gpt", "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-03T00:00:00"},
])
db.coach_chats.insert_many([
    {"id": "cA37", "user_id": owner["id"], "session_id": "uiA37", "message": "TEST_alpha question", "reply": "ALPHA reply", "pois": [], "created_at": "2026-01-02T00:00:00"},
    {"id": "cB37", "user_id": owner["id"], "session_id": "uiB37", "message": "TEST_beta question", "reply": "BETA reply", "pois": [], "created_at": "2026-01-03T00:00:00"},
])
print("seeded")
