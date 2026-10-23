# Iteration 40: AI expense extraction, proof validation, manual expense CRUD, RBAC
import base64
import io
import os

import pytest
import requests
from PIL import Image, ImageDraw

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
TODAY = "2026-01-15"


def receipt_image(fmt="JPEG"):
    img = Image.new("RGB", (480, 720), "white")
    d = ImageDraw.Draw(img)
    lines = ["TOKO SUSU MAKMUR", "Jl. Merdeka 12 Bandung", "Tgl: 15-01-2026 10:22",
             "-----------------------------", "Susu UHT 1L  x4    72.000", "Gula Aren 1kg x1   28.000",
             "Cup Plastik 16oz x50 45.000", "-----------------------------", "TOTAL            145.000",
             "TUNAI            150.000", "KEMBALI            5.000", "Terima kasih"]
    for i, t in enumerate(lines):
        d.text((30, 40 + i * 50), t, fill="black")
    for x in range(0, 480, 12):
        d.line([(x, 700), (x + 6, 715)], fill=(40, 40, 40))
    buf = io.BytesIO()
    img.save(buf, fmt, quality=85) if fmt == "JPEG" else img.save(buf, fmt)
    mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[fmt]
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def blank_png():
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), "white").save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@pytest.fixture(scope="module")
def owner():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/identify", json={"identifier": "baa", "terms_accepted": True, "privacy_accepted": True})
    assert r.status_code == 200, r.text
    tok = r.json().get("account_token")
    r = s.post(f"{BASE_URL}/api/auth/login", json={"account_token": tok, "pin": "130994", "remember": True})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "owner"
    return s


@pytest.fixture(scope="module")
def created(owner):
    ids = []
    yield ids
    for i in ids:
        owner.delete(f"{BASE_URL}/api/expenses/{i}")


def count_expenses(s):
    r = s.get(f"{BASE_URL}/api/expenses", params={"start": "2000-01-01", "end": "2100-01-01"})
    assert r.status_code == 200
    return len(r.json())


# RBAC
class TestRBAC:
    def test_unauth_extract(self):
        r = requests.post(f"{BASE_URL}/api/expenses/extract", json={"proof": receipt_image()})
        assert r.status_code in (401, 403)

    def test_unauth_create(self):
        r = requests.post(f"{BASE_URL}/api/expenses", json={"date": TODAY, "category": "Other", "amount": 1000})
        assert r.status_code in (401, 403)

    def test_unauth_list_delete(self):
        assert requests.get(f"{BASE_URL}/api/expenses", params={"start": TODAY, "end": TODAY}).status_code in (401, 403)
        assert requests.delete(f"{BASE_URL}/api/expenses/xyz").status_code in (401, 403)


# Proof validation
class TestProofValidation:
    @pytest.mark.parametrize("proof", [
        "data:image/svg+xml;base64," + base64.b64encode(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>").decode(),
        "data:image/png;base64,@@@notbase64@@@",
        "data:image/png;base64," + base64.b64encode(b"x" * 500).decode(),
        "not-a-data-url",
    ])
    def test_invalid_rejected(self, owner, proof):
        r = owner.post(f"{BASE_URL}/api/expenses/extract", json={"proof": proof})
        assert 400 <= r.status_code < 500, r.text

    def test_blank_rejected(self, owner):
        r = owner.post(f"{BASE_URL}/api/expenses/extract", json={"proof": blank_png()})
        assert r.status_code == 400
        assert "kosong" in r.json().get("detail", "").lower()

    def test_create_with_invalid_proof_rejected(self, owner):
        r = owner.post(f"{BASE_URL}/api/expenses", json={"date": TODAY, "category": "Other", "amount": 1000,
                                                        "note": "TEST_QA bad", "proof": blank_png()})
        assert r.status_code == 400


# Manual expense CRUD
class TestManualExpense:
    def test_create_list_finance_delete(self, owner, created):
        r = owner.post(f"{BASE_URL}/api/expenses", json={"date": TODAY, "category": "Packaging", "amount": 12345,
                                                        "account": "bank", "note": "TEST_QA manual"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["amount"] == 12345 and d["category"] == "Packaging" and d["account"] == "bank"
        created.append(d["id"])
        lst = owner.get(f"{BASE_URL}/api/expenses", params={"start": TODAY, "end": TODAY}).json()
        assert any(e["id"] == d["id"] for e in lst)
        fs = owner.get(f"{BASE_URL}/api/finance/summary", params={"start": TODAY, "end": TODAY})
        assert fs.status_code == 200
        assert d["id"] in fs.text
        assert owner.delete(f"{BASE_URL}/api/expenses/{d['id']}").status_code == 200
        lst = owner.get(f"{BASE_URL}/api/expenses", params={"start": TODAY, "end": TODAY}).json()
        assert not any(e["id"] == d["id"] for e in lst)

    @pytest.mark.parametrize("body", [
        {"date": TODAY, "category": "Bogus", "amount": 1000},
        {"date": TODAY, "category": "Other", "amount": 0},
        {"date": TODAY, "category": "Other", "amount": 1000, "account": "crypto"},
    ])
    def test_create_validation(self, owner, body):
        assert owner.post(f"{BASE_URL}/api/expenses", json=body).status_code in (400, 422)


# Expense with proof
class TestProofExpense:
    def test_save_with_png_proof(self, owner, created):
        r = owner.post(f"{BASE_URL}/api/expenses", json={"date": TODAY, "category": "Raw Material", "amount": 145000,
                                                        "note": "TEST_QA proof", "proof": receipt_image("PNG"),
                                                        "extraction": {"merchant": "TOKO", "items": ["Susu"]}})
        assert r.status_code == 200, r.text
        d = r.json()
        created.append(d["id"])
        assert d["proof"].startswith("/api/expenses/"), d["proof"][:60]
        assert d["extraction"]["merchant"] == "TOKO"
        fs = owner.get(f"{BASE_URL}/api/finance/summary", params={"start": TODAY, "end": TODAY}).text
        assert d["proof"] in fs
        f = owner.get(f"{BASE_URL}{d['proof']}")
        assert f.status_code == 200 and f.headers["content-type"].startswith("image/png")
        TestProofExpense.proof_url = d["proof"]

    def test_proof_file_requires_auth(self):
        url = getattr(TestProofExpense, "proof_url", None)
        if not url:
            pytest.skip("no proof")
        r = requests.get(f"{BASE_URL}{url}")
        assert r.status_code in (401, 403), f"proof file publicly accessible: {r.status_code}"


# Live AI extraction (single call), must not persist
class TestLiveExtraction:
    def test_extract_draft_no_persist(self, owner):
        before = count_expenses(owner)
        r = owner.post(f"{BASE_URL}/api/expenses/extract", json={"proof": receipt_image("JPEG")}, timeout=120)
        print("EXTRACT", r.status_code, r.text[:600])
        assert r.status_code in (200, 424), r.text
        if r.status_code == 200:
            d = r.json()
            for k in ("date", "category", "amount", "account", "note", "merchant", "items"):
                assert k in d
            assert isinstance(d["amount"], (int, float)) and isinstance(d["items"], list)
        else:
            assert "manual" in r.json()["detail"].lower()
        assert count_expenses(owner) == before
