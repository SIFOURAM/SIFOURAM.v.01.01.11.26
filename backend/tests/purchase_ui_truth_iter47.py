# Iter47: Owner access to Purchase data + AI extract response shape (does it return line items mappable to materials?)
import json, requests
BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL")][0]


def login(i, p):
    s = requests.Session()
    t = s.post(f"{BASE}/api/auth/identify", json={"identifier": i, "terms_accepted": True, "privacy_accepted": True}).json()
    s.post(f"{BASE}/api/auth/login", json={"account_token": t.get("account_token") or t.get("token"), "pin": p, "remember": False}).raise_for_status()
    return s


o = login("baa", "130994")
print("owner PO list", o.get(f"{BASE}/api/purchase-orders").status_code, "materials", o.get(f"{BASE}/api/materials").status_code)
import base64
data = "data:image/png;base64," + base64.b64encode(open("/tmp/iter46_proof.png", "rb").read()).decode()
r = o.post(f"{BASE}/api/expenses/extract", json={"proof": data}, timeout=120)
print("extract", r.status_code, r.text[:600])
if r.ok:
    j = r.json()
    print("keys", list(j.keys()), "items type", type(j.get("items")).__name__, json.dumps(j.get("items"))[:300])
