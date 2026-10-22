# Iteration 37: Coach chat sessions (CRUD, ownership isolation, session-scoped chat with mocked LLM).
import asyncio
import os
import sys
import types
import uuid

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
RIDER = (f"test_r37_{uuid.uuid4().hex[:6]}", "373737")
STATE = {}


def identify(s, ident):
    return s.post(f"{API}/auth/identify", json={"identifier": ident, "terms_accepted": True, "privacy_accepted": True})


def login(ident, pin):
    s = requests.Session()
    r = identify(s, ident)
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/auth/login", json={"account_token": r.json()["account_token"], "pin": pin, "remember": True})
    assert r.status_code == 200, r.text
    return s


def cleanup():
    ids = [u["id"] for u in db.users.find({"username": {"$regex": "^test_r37_"}}, {"id": 1})]
    for c in ("sessions", "audit_logs", "login_attempts", "coach_sessions", "coach_chats"):
        db[c].delete_many({"user_id": {"$in": ids}})
    db.users.delete_many({"id": {"$in": ids}})
    db.coach_sessions.delete_many({"title": {"$regex": "^TEST_"}})
    db.coach_chats.delete_many({"message": {"$regex": "^TEST_"}})
    sids = [STATE[k] for k in ("s1", "s2") if k in STATE]
    db.coach_sessions.delete_many({"id": {"$in": sids}})
    db.coach_chats.delete_many({"session_id": {"$in": sids}})


@pytest.fixture(scope="module", autouse=True)
def module_data():
    cleanup()
    yield
    cleanup()


@pytest.fixture(scope="module")
def owner():
    return login("baa", "130994")


@pytest.fixture(scope="module")
def rider(owner):
    r = owner.post(f"{API}/users", json={"name": "TEST Rider37", "username": RIDER[0], "pin": RIDER[1], "role": "rider", "active": True})
    assert r.status_code == 200, r.text
    STATE["rid"] = r.json()["id"]
    return login(RIDER[0], RIDER[1])


class TestCoachSessionCrud:
    def test_create_and_list(self, owner):
        r = owner.post(f"{API}/coach/sessions", json={"provider": "gpt"})
        assert r.status_code == 200, r.text
        s = r.json()
        assert s["title"] == "Chat baru" and isinstance(s["id"], str) and "_id" not in s
        STATE["s1"] = s["id"]
        r2 = owner.post(f"{API}/coach/sessions", json={})
        STATE["s2"] = r2.json()["id"]
        lst = owner.get(f"{API}/coach/sessions").json()
        ids = [x["id"] for x in lst]
        assert STATE["s1"] in ids and STATE["s2"] in ids
        assert all("_id" not in x for x in lst)

    def test_rename_persists(self, owner):
        r = owner.put(f"{API}/coach/sessions/{STATE['s1']}", json={"title": "  TEST_renamed  "})
        assert r.status_code == 200 and r.json()["ok"] is True
        lst = owner.get(f"{API}/coach/sessions").json()
        assert next(x for x in lst if x["id"] == STATE["s1"])["title"] == "TEST_renamed"
        assert lst[0]["id"] == STATE["s1"]  # sorted by updated_at desc

    def test_rename_validation(self, owner):
        assert owner.put(f"{API}/coach/sessions/{STATE['s1']}", json={"title": ""}).status_code == 422
        assert owner.put(f"{API}/coach/sessions/{STATE['s1']}", json={"title": "x" * 81}).status_code == 422

    def test_messages_empty(self, owner):
        r = owner.get(f"{API}/coach/sessions/{STATE['s1']}/messages")
        assert r.status_code == 200 and r.json() == []

    def test_not_found(self, owner):
        assert owner.get(f"{API}/coach/sessions/nope/messages").status_code == 404
        assert owner.put(f"{API}/coach/sessions/nope", json={"title": "a"}).status_code == 404
        assert owner.delete(f"{API}/coach/sessions/nope").status_code == 404

    def test_unauthenticated(self):
        assert requests.get(f"{API}/coach/sessions").status_code == 401

    def test_cross_user_isolation(self, owner, rider):
        # seed messages directly into both owner sessions
        db.coach_chats.insert_many([
            {"id": uuid.uuid4().hex, "user_id": owner_id(owner), "session_id": STATE["s1"], "message": "TEST_m1", "reply": "r1", "created_at": "2026-01-01T00:00:00"},
            {"id": uuid.uuid4().hex, "user_id": owner_id(owner), "session_id": STATE["s2"], "message": "TEST_m2", "reply": "r2", "created_at": "2026-01-01T00:00:01"},
        ])
        assert rider.get(f"{API}/coach/sessions/{STATE['s1']}/messages").status_code == 404
        assert rider.put(f"{API}/coach/sessions/{STATE['s1']}", json={"title": "hack"}).status_code == 404
        assert rider.delete(f"{API}/coach/sessions/{STATE['s1']}").status_code == 404
        assert rider.post(f"{API}/coach/chat", json={"message": "TEST_x", "session_id": STATE["s1"]}).status_code == 404
        assert STATE["s1"] not in [x["id"] for x in rider.get(f"{API}/coach/sessions").json()]
        assert rider.get(f"{API}/coach/history", params={"session_id": STATE["s1"]}).status_code == 404
        msgs = owner.get(f"{API}/coach/sessions/{STATE['s1']}/messages").json()
        assert [m["message"] for m in msgs] == ["TEST_m1"]

    def test_delete_only_own_messages(self, owner):
        assert owner.delete(f"{API}/coach/sessions/{STATE['s1']}").status_code == 200
        assert owner.get(f"{API}/coach/sessions/{STATE['s1']}/messages").status_code == 404
        assert db.coach_chats.count_documents({"session_id": STATE["s1"]}) == 0
        msgs = owner.get(f"{API}/coach/sessions/{STATE['s2']}/messages").json()
        assert [m["message"] for m in msgs] == ["TEST_m2"]


def owner_id(s):
    if "oid" not in STATE:
        b = s.get(f"{API}/auth/me").json()
        STATE["oid"] = b.get("user", b)["id"]
    return STATE["oid"]


class TestCoachChatMockedLLM:
    """Runs the FastAPI app in-process with a fake emergentintegrations LlmChat (no token spend)."""

    def test_chat_session_scoping(self):
        captured = []

        class FakeChat:
            def __init__(self, api_key, session_id, system_message):
                captured.append({"session_id": session_id, "system": system_message})

            def with_model(self, *a):
                return self

            async def send_message(self, msg):
                return f"MOCK reply to {msg.text}"

        class FakeUserMessage:
            def __init__(self, text):
                self.text = text

        mod = types.ModuleType("emergentintegrations.llm.chat")
        mod.LlmChat = FakeChat
        mod.UserMessage = FakeUserMessage
        saved = sys.modules.get("emergentintegrations.llm.chat")
        sys.modules["emergentintegrations.llm.chat"] = mod
        sys.path.insert(0, "/app/backend")
        import httpx
        import server

        async def run():
            transport = httpx.ASGITransport(app=server.app)
            async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as c:
                tok = (await c.post("/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})).json()["account_token"]
                r = await c.post("/api/auth/login", json={"account_token": tok, "pin": "130994", "remember": True})
                assert r.status_code == 200, r.text
                sa = (await c.post("/api/coach/sessions", json={})).json()["id"]
                sb = (await c.post("/api/coach/sessions", json={})).json()["id"]
                r = await c.post("/api/coach/chat", json={"message": "TEST_alpha_secret", "session_id": sa})
                assert r.status_code == 200, r.text
                d = r.json()
                assert d["session_id"] == sa and d["reply"] == "MOCK reply to TEST_alpha_secret" and "_id" not in d
                r = await c.post("/api/coach/chat", json={"message": "TEST_beta_q", "session_id": sb})
                assert r.status_code == 200 and r.json()["session_id"] == sb
                # second message in A should include A history only
                r = await c.post("/api/coach/chat", json={"message": "TEST_alpha_two", "session_id": sa})
                assert r.status_code == 200
                ma = (await c.get(f"/api/coach/sessions/{sa}/messages")).json()
                mb = (await c.get(f"/api/coach/sessions/{sb}/messages")).json()
                sessions = (await c.get("/api/coach/sessions")).json()
                # no session_id -> auto-create
                r = await c.post("/api/coach/chat", json={"message": "TEST_auto"})
                auto = r.json()["session_id"]
                for sid in (sa, sb, auto):
                    await c.delete(f"/api/coach/sessions/{sid}")
                return sa, sb, ma, mb, sessions, auto

        try:
            sa, sb, ma, mb, sessions, auto = asyncio.run(run())
        finally:
            if saved is not None:
                sys.modules["emergentintegrations.llm.chat"] = saved
        assert [m["message"] for m in ma] == ["TEST_alpha_secret", "TEST_alpha_two"]
        assert [m["message"] for m in mb] == ["TEST_beta_q"]
        assert captured[0]["session_id"].endswith(f"-{sa}") and captured[1]["session_id"].endswith(f"-{sb}")
        assert "TEST_alpha_secret" not in captured[1]["system"], "session B prompt leaked session A history"
        assert "TEST_alpha_secret" in captured[2]["system"] and "TEST_beta_q" not in captured[2]["system"]
        titles = {s["id"]: s["title"] for s in sessions}
        assert titles[sa] == "TEST_alpha_secret" and titles[sb] == "TEST_beta_q"
        assert auto and auto not in (sa, sb)
        assert db.coach_sessions.count_documents({"id": {"$in": [sa, sb, auto]}}) == 0
