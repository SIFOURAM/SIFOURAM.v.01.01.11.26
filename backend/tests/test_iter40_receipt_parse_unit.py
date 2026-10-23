# Iteration 40: isolated unit tests for receipt JSON parsing/draft normalisation (no model calls)
import sys

import pytest

sys.path.insert(0, "/app/backend")
from fastapi import HTTPException  # noqa: E402
from server import receipt_draft, receipt_json  # noqa: E402


def test_fenced_json_parsed():
    d = receipt_draft(receipt_json('```json\n{"date":"2026-01-15","merchant":"Toko","amount":"145000","category":"Raw Material","account":"cash","items":["Susu"]}\n```'))
    assert d["amount"] == 145000 and d["category"] == "Raw Material" and d["merchant"] == "Toko" and d["items"] == ["Susu"]


def test_invalid_values_normalised():
    d = receipt_draft({"date": "15/01/2026", "category": "Food", "amount": "abc", "account": "QRIS", "items": "x"})
    assert d["category"] == "Other" and d["amount"] == 0 and d["account"] == "cash" and d["items"] == []
    assert len(d["date"]) == 10


def test_negative_amount_clamped():
    assert receipt_draft({"amount": -500})["amount"] == 0


@pytest.mark.parametrize("text", ["not json", "[1,2]"])
def test_bad_model_output_424(text):
    with pytest.raises(HTTPException) as e:
        receipt_json(text)
    assert e.value.status_code == 424
