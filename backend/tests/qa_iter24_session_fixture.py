# Session-policy QA fixture: create temp rider/barteam/admin, issue tokens; cleanup removes them
import os, sys, json, requests, asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv("/app/backend/.env"); load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
STATE = "/tmp/qa_iter24_state.json"
USERS = [("qa24_rider", "rider"), ("qa24_bar", "barteam"), ("qa24_admin", "admin")]


def tok(ident, pin):
    r = requests.post(f"{BASE}/auth/identify", json={"identifier": ident, "terms_accepted": True, "privacy_accepted": True})
    r.raise_for_status()
    r = requests.post(f"{BASE}/auth/login", json={"account_token": r.json()["account_token"] if "account_token" in r.json() else r.json()["token"], "pin": pin, "remember": True})
    r.raise_for_status()
    return r.json()["token"]


def setup():
    owner = tok("baa", "130994")
    h = {"Authorization": f"Bearer {owner}"}
    st = {"owner": owner}
    for un, role in USERS:
        r = requests.post(f"{BASE}/users", headers=h, json={"name": un.upper(), "username": un, "role": role, "pin": "246813"})
        print(un, r.status_code, r.text[:120])
        st[role] = tok(un, "246813")
    json.dump(st, open(STATE, "w")); print(json.dumps({k: v[:15] for k, v in st.items()}))


async def cleanup():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    names = [u for u, _ in USERS]
    r = await db.users.delete_many({"username": {"$in": names}})
    print("deleted users", r.deleted_count)


if __name__ == "__main__":
    setup() if sys.argv[1] == "setup" else asyncio.run(cleanup())
