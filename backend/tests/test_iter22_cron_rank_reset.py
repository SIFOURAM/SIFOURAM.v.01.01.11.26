# Iter22: weekly-rank-reset cron endpoint auth + idempotency, crons.yml validity
import os
import uuid
import pytest
import requests
import yaml
from dotenv import dotenv_values

BASE_URL = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
SECRET = dotenv_values("/app/backend/.env").get("WEBHOOK_CRON_SECRET")
URL = f"{BASE_URL}/api/cron/weekly-rank-reset"


def test_crons_yml_valid():
    data = yaml.safe_load(open("/app/.emergent/crons.yml"))
    job = [c for c in data["crons"] if c["name"] == "weekly-rank-reset"][0]
    assert job["cron"] == "0 0 * * 1"
    assert job["timezone"] == "Asia/Jakarta"
    assert job["method"] == "POST"
    assert job["endpoint"].endswith("/api/cron/weekly-rank-reset")


def test_missing_auth_rejected():
    r = requests.post(URL, json={"run_id": "TEST_x"})
    assert r.status_code == 401


def test_wrong_secret_rejected():
    r = requests.post(URL, json={"run_id": "TEST_x"}, headers={"Authorization": "Bearer wrong-secret"})
    assert r.status_code == 401


def test_no_bearer_prefix_raw_secret():
    # raw secret without "Bearer " — removeprefix leaves it untouched, document behaviour
    r = requests.post(URL, json={"run_id": "TEST_x"}, headers={"Authorization": SECRET})
    print("raw-secret status", r.status_code)


def test_empty_body_missing_auth():
    # Cron schedulers may POST without a JSON body
    r = requests.post(URL)
    print("empty body no auth", r.status_code, r.text[:200])
    assert r.status_code == 401


def test_empty_body_valid_auth_with_webhook_id():
    r = requests.post(URL, headers={"Authorization": f"Bearer {SECRET}", "X-Webhook-Id": f"TEST_qa_{uuid.uuid4().hex[:8]}"})
    print("empty body valid auth", r.status_code, r.text[:200])
    assert r.status_code == 200


def test_valid_and_idempotent():
    rid = f"TEST_qa_{uuid.uuid4().hex[:8]}"
    h = {"Authorization": f"Bearer {SECRET}", "X-Webhook-Id": rid}
    r1 = requests.post(URL, json={}, headers=h)
    assert r1.status_code == 200 and r1.json().get("ok") is True
    import time; time.sleep(1.5)
    r2 = requests.post(URL, json={}, headers=h)
    assert r2.status_code == 200
    assert r2.json().get("duplicate") is True


def test_valid_missing_run_id():
    r = requests.post(URL, json={}, headers={"Authorization": f"Bearer {SECRET}"})
    assert r.status_code == 400
