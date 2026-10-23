# Iteration 42: Google managed auth endpoint safety, PIN login regression, coach model map
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def owner_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    if r.status_code == 429:
        time.sleep(61)
        r = s.post(f"{API}/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    tok = r.json()["account_token"]
    r = s.post(f"{API}/auth/login", json={"account_token": tok, "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    return s, r


@pytest.fixture(scope="module")
def owner():
    s, r = owner_session()
    yield s, r
    s.post(f"{API}/auth/logout")


# PIN login regression + HttpOnly cookie
class TestPinLogin:
    def test_pin_login_sets_httponly_cookie(self, owner):
        s, r = owner
        sc = r.headers.get("set-cookie", "")
        assert "si4am_session=" in sc
        assert "httponly" in sc.lower()
        assert "secure" in sc.lower()
        body = r.json()
        assert "token" not in body and "access_token" not in body
        assert body["user"]["role"] == "owner"
        assert body["user"]["email"] == "baazulfikar@gmail.com"

    def test_me_with_cookie(self, owner):
        s, _ = owner
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "owner"

    def test_me_without_cookie_401(self):
        assert requests.get(f"{API}/auth/me").status_code == 401


# Google session endpoint safety
class TestGoogleSession:
    def test_missing_session_id_400(self):
        r = requests.post(f"{API}/auth/google/session", json={})
        assert r.status_code == 400
        assert "si4am_session" not in r.headers.get("set-cookie", "")

    def test_blank_session_id_400(self):
        r = requests.post(f"{API}/auth/google/session", json={"session_id": "   "})
        assert r.status_code == 400

    def test_invalid_session_id_no_cookie(self):
        r = requests.post(f"{API}/auth/google/session", json={"session_id": "TEST_invalid_session_xyz"})
        print("invalid session status", r.status_code, r.text[:200])
        assert r.status_code in (401, 403, 502)
        assert "si4am_session" not in r.headers.get("set-cookie", "")
        assert "user" not in (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})

    def test_non_json_body(self):
        r = requests.post(f"{API}/auth/google/session", data="x", headers={"Content-Type": "application/json"})
        assert r.status_code in (400, 422)


# Coach model choices: each provider must actually work
@pytest.mark.parametrize("provider", ["gemini", "gpt-terra", "gpt", "claude-sonnet", "claude"])
def test_coach_provider(owner, provider):
    s, _ = owner
    r = s.post(f"{API}/coach/chat", json={"message": "TEST_ halo singkat saja", "provider": provider}, timeout=120)
    print(provider, r.status_code, r.text[:300])
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["provider"] == provider
    assert isinstance(d["reply"], str) and len(d["reply"]) > 0
    # cleanup session
    s.delete(f"{API}/coach/sessions/{d['session_id']}")
