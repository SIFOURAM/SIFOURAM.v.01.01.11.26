# Regresi absensi POS iterasi 52 - isi skrip browser dengan objek `page` tersedia.
# Login Owner asli untuk uji awal; seluruh data Rider/stok/absensi/EOD memakai fixture browser khusus pengujian.
# Permintaan checkin dan eod/close dijawab fixture; POST /api/sales dibatalkan demi keamanan.
import json, asyncio, base64, re

# Ambil URL dari frontend/.env dan kredensial Owner dari memory (tanpa hardcode, tidak dicetak)
def _env(key):
    for ln in open("/app/frontend/.env"):
        if ln.startswith(key + "="): return ln.split("=", 1)[1].strip()
BASE = _env("REACT_APP_BACKEND_URL").rstrip("/")
_row = [c.strip() for c in re.search(r"^\|\s*owner\s*\|.*$", open("/app/memory/test_credentials.md").read(), re.M).group(0).strip("|").split("|")]
OWNER_ID, OWNER_PIN = _row[1], _row[4]
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
results = []
def rec(name, ok, extra=""):
    results.append((name, ok)); print(("PASS " if ok else "FAIL ") + name + (" | " + extra if extra else ""))

errors = []
page.on("pageerror", lambda e: errors.append(str(e)))

S = {"att": {}, "delay": {}, "fail": set(), "checkin_posts": 0, "att_gets": 0, "closed": False,
     "close_posts": 0, "sales_posts": 0}
RIDERS = [{"id": "fx_rider_a", "name": "FX Rider A", "role": "rider", "active": True},
          {"id": "fx_rider_b", "name": "FX Rider B", "role": "rider", "active": True}]

async def fx(route, request):
    url = request.url; m = request.method
    path = url.split("/api", 1)[1].split("?")[0]
    q = dict(re.findall(r"[?&]([^=&]+)=([^&]*)", url))
    def ok(data): return route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
    if path == "/users" and q.get("role") == "rider": return await ok(RIDERS)
    if path == "/attendance" and m == "GET":
        S["att_gets"] += 1; rid = q.get("rider_id"); d = q.get("start")
        if S["delay"].get(rid): await asyncio.sleep(S["delay"][rid])
        if rid in S["fail"]: return await route.fulfill(status=500, content_type="application/json", body=json.dumps({"detail": "fixture failure"}))
        r = S["att"].get((rid, d)); return await ok([r] if r else [])
    if path == "/attendance/checkin" and m == "POST":
        S["checkin_posts"] += 1; b = json.loads(request.post_data or "{}")
        r = {"id": "fx_att_" + b["rider_id"], "rider_id": b["rider_id"], "date": b["date"],
             "checkin_at": "2026-01-15T08:00:00+07:00", "checkin_time": "08:00", "checkin_photo": b.get("photo")}
        S["att"][(b["rider_id"], b["date"])] = r; return await ok(r)
    if path == "/pos/stock":
        return await ok({"has_stock": True, "closed": S["closed"], "deposited": False,
                         "items": [{"menu_id": "fxm1", "name": "FX Kopi", "price": 15000, "photo": "", "remaining": 5, "stock": 5, "sold": 0, "initial": 5}]})
    if path.startswith("/payment-accounts/public"): return await ok([])
    if path == "/customers/lookup": return await ok({"customers": []})
    if path == "/sales/eod" and m == "GET":
        return await ok({"date": q.get("date"), "transactions": 0, "rows": [{"menu_id": "fxm1", "name": "FX Kopi", "initial": 5, "remaining": 5, "cash_qty": 0, "qris_qty": 0}],
                         "total_cups": 0, "total_cash": 0, "total_qris": 0, "total": 0, "closed": S["closed"]})
    if path == "/sales/eod/close" and m == "POST":
        S["close_posts"] += 1; S["closed"] = True; b = json.loads(request.post_data or "{}")
        return await ok({"date": b.get("date"), "transactions": 0, "rows": [{"menu_id": "fxm1", "name": "FX Kopi", "initial": 5, "remaining": 5, "cash_qty": 0, "qris_qty": 0}],
                         "total_cups": 0, "total_cash": 0, "total_qris": 0, "total": 0, "closed": True})
    if path == "/sales" and m == "POST":
        S["sales_posts"] += 1; return await route.abort()
    return await route.continue_()

async def dis(tid): return await page.get_by_test_id(tid).is_disabled()
async def pick(rid): await page.get_by_test_id("pos-rider-select").select_option(rid)
async def ready_wait(): await page.wait_for_selector('[data-testid="attendance-loading"]', state="detached", timeout=8000)

try:
    await page.set_viewport_size({"width": 1920, "height": 800})
    r = await page.request.post(f"{BASE}/api/auth/identify", data={"identifier": OWNER_ID, "terms_accepted": True, "privacy_accepted": True})
    tok = (await r.json()).get("account_token")
    r2 = await page.request.post(f"{BASE}/api/auth/login", data={"account_token": tok, "pin": OWNER_PIN, "remember": True})
    rec("owner login 200", r2.status == 200)

    # --- Smoke: direct /pos (real API, no fixtures)
    await page.goto(f"{BASE}/pos"); await page.wait_for_selector('[data-testid="pos-page"]', timeout=15000)
    rec("desktop direct /pos visible", await page.get_by_test_id("pos-page").is_visible())
    rec("owner no rider: absen disabled", await dis("absen-button"))
    rec("owner no rider: eod disabled", await dis("eod-button"))
    rec("rider select in header", await page.locator('header [data-testid="pos-rider-select"], [data-testid="pos-page"] > *:first-child [data-testid="pos-rider-select"]').count() > 0)
    # via navigation
    await page.goto(f"{BASE}/"); await page.wait_for_timeout(2000)
    link = page.get_by_test_id("nav-category-pos")
    if await link.count():
        await link.click(force=True); await page.wait_for_timeout(1000)
        await page.get_by_test_id("category-tabs-dropdown").select_option("/pos"); await page.wait_for_selector('[data-testid="pos-page"]', timeout=10000)
        rec("desktop nav /pos visible", True)
    else: rec("desktop nav link /pos found", False)
    rec("no pageerror (desktop smoke)", not errors, "; ".join(errors))

    # --- Fixtures on
    await page.route("**/api/**", fx)
    await page.goto(f"{BASE}/pos"); await page.wait_for_selector('[data-testid="pos-page"]')
    await page.wait_for_timeout(1000)
    await pick("fx_rider_a"); await ready_wait()
    rec("A empty: absen enabled", not await dis("absen-button"))
    rec("A empty: eod disabled", await dis("eod-button"))
    await page.get_by_test_id("absen-button").click()
    await page.wait_for_selector('[data-testid="absen-dialog"]')
    rec("checkin disabled w/o pin+photo", await dis("checkin-button"))
    await page.get_by_test_id("attendance-pin-input").fill("12345")
    rec("checkin disabled 5-digit pin", await dis("checkin-button"))
    await page.get_by_test_id("attendance-pin-input").fill(""); await page.get_by_test_id("attendance-pin-input").press_sequentially("12a3456789")
    rec("pin input digits only max 6", (await page.get_by_test_id("attendance-pin-input").input_value()) == "123456", await page.get_by_test_id("attendance-pin-input").input_value())
    rec("checkin disabled w/o photo", await dis("checkin-button"))
    await page.locator('[data-testid="absen-dialog"] input[type=file]').set_input_files({"name": "a.png", "mimeType": "image/png", "buffer": PNG})
    await page.wait_for_timeout(800)
    rec("checkin enabled with pin+photo", not await dis("checkin-button"))
    await page.get_by_test_id("checkin-button").click()
    await page.wait_for_selector('[data-testid="absen-dialog"]', state="detached", timeout=10000)
    rec("dialog closed after checkin", True)
    rec("checkin posted once", S["checkin_posts"] == 1, str(S["checkin_posts"]))
    rec("absen 'Sudah Absen' disabled", await dis("absen-button") and "Sudah Absen" in (await page.get_by_test_id("absen-button").inner_text()))
    rec("eod enabled after checkin (no reload)", not await dis("eod-button"))
    await page.get_by_test_id("absen-button").click(force=True); await page.wait_for_timeout(500)
    rec("no dialog reopen after absen", await page.get_by_test_id("absen-dialog").count() == 0)
    rec("rider select still available after absen", await page.get_by_test_id("pos-rider-select").is_enabled())

    # per-rider
    await pick("fx_rider_b"); await ready_wait()
    rec("B: absen enabled / eod disabled", (not await dis("absen-button")) and await dis("eod-button"))
    await pick("fx_rider_a"); await ready_wait()
    rec("back to A: eod enabled", not await dis("eod-button"))

    # reload with existing attendance
    await page.reload(); await page.wait_for_selector('[data-testid="pos-page"]'); await page.wait_for_timeout(800)
    await pick("fx_rider_a"); await ready_wait()
    rec("reload existing att: eod enabled, absen disabled", (not await dis("eod-button")) and await dis("absen-button"))

    # stale response: A delayed (has att), switch to B quickly
    await pick("fx_rider_b"); await ready_wait()
    S["delay"]["fx_rider_a"] = 3
    await pick("fx_rider_a"); await page.wait_for_timeout(300)
    loading_vis = await page.get_by_test_id("attendance-loading").is_visible()
    rec("A loading: loading shown, absen+eod disabled", loading_vis and await dis("absen-button") and await dis("eod-button"))
    await pick("fx_rider_b"); await page.wait_for_timeout(3800)
    rec("stale A not borrowed by B", (not await dis("absen-button")) and await dis("eod-button") and "Sudah" not in await page.get_by_test_id("absen-button").inner_text())
    S["delay"] = {}

    # failure + retry
    S["fail"].add("fx_rider_b")
    await pick("fx_rider_a"); await ready_wait(); await pick("fx_rider_b")
    await page.wait_for_selector('[data-testid="attendance-load-error"]', timeout=8000)
    rec("error shown, absen+eod disabled", await dis("absen-button") and await dis("eod-button"))
    S["fail"].clear()
    await page.get_by_test_id("attendance-retry-button").click()
    await page.wait_for_selector('[data-testid="attendance-load-error"]', state="detached", timeout=8000); await ready_wait()
    rec("retry succeeded", not await dis("absen-button"))

    # cart + realtime with draft
    await page.get_by_test_id("pos-product-fxm1").click(); await page.get_by_test_id("pos-product-fxm1").click()
    fb = await page.get_by_test_id("pos-cart-floating-button").inner_text()
    rec("cart floating total 30.000", "30.000" in fb or "30,000" in fb, fb)
    await page.get_by_test_id("absen-button").click(); await page.wait_for_selector('[data-testid="absen-dialog"]')
    await page.get_by_test_id("attendance-pin-input").fill("654321")
    await page.locator('[data-testid="absen-dialog"] input[type=file]').set_input_files({"name": "b.png", "mimeType": "image/png", "buffer": PNG})
    await page.wait_for_timeout(800)
    gets_before = S["att_gets"]
    await page.evaluate("window.dispatchEvent(new Event('si4am:data-changed'))"); await page.wait_for_timeout(1500)
    rec("realtime refetched attendance", S["att_gets"] > gets_before)
    rec("draft PIN kept", (await page.get_by_test_id("attendance-pin-input").input_value()) == "654321")
    rec("draft photo kept", await page.locator('[data-testid="attendance-photo"] img').count() == 1)
    await page.get_by_test_id("checkin-button").click()
    await page.wait_for_selector('[data-testid="absen-dialog"]', state="detached", timeout=10000)
    rec("B checkin posted (total 2)", S["checkin_posts"] == 2, str(S["checkin_posts"]))
    fb2 = await page.get_by_test_id("pos-cart-floating-button").inner_text()
    rec("cart kept after realtime+checkin", fb2 == fb, fb2)
    await page.get_by_test_id("pos-cart-floating-button").click()
    ct = await page.get_by_test_id("cart-total").inner_text()
    rec("cart-total 30.000", "30.000" in ct or "30,000" in ct, ct)
    await page.get_by_test_id("pos-payment-sheet").click(position={"x": 960, "y": 150}); await page.wait_for_timeout(500)
    rec("payment sheet closes on backdrop click", await page.get_by_test_id("pos-payment-sheet").count() == 0)

    # EOD
    await page.get_by_test_id("eod-button").click()
    await page.wait_for_selector('[data-testid="eod-receipt"]', timeout=8000)
    rec("eod receipt open", True)
    await page.get_by_test_id("eod-close-button").click(); await page.wait_for_timeout(1500)
    rec("eod close posted once", S["close_posts"] == 1)
    rec("eod-close-button gone (closed)", await page.get_by_test_id("eod-close-button").count() == 0)
    await page.screenshot(path=".screenshots/iter52_eod_closed.jpg", quality=20, full_page=False)
    await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
    rec("pos-locked visible", await page.get_by_test_id("pos-locked").is_visible())
    rec("product disabled when locked", await dis("pos-product-fxm1"))
    rec("no sales POST made", S["sales_posts"] == 0)
    await page.unroute("**/api/**")

    # --- Mobile smoke (real API)
    await page.set_viewport_size({"width": 390, "height": 844})
    await page.goto(f"{BASE}/pos"); await page.wait_for_selector('[data-testid="pos-page"]', timeout=15000)
    rec("mobile /pos visible; absen+eod disabled", await dis("absen-button") and await dis("eod-button"))
    await page.goto(f"{BASE}/"); await page.wait_for_timeout(1500)
    await page.get_by_test_id("bottomnav-pos").click(); await page.wait_for_timeout(1000)
    await page.get_by_test_id("category-tabs-dropdown").select_option("/pos"); await page.wait_for_selector('[data-testid="pos-page"]', timeout=10000)
    rec("mobile nav bottomnav-pos -> pos-page", True)
    await page.screenshot(path=".screenshots/iter52_mobile_pos.jpg", quality=20, full_page=False)
    rec("no pageerror overall", not errors, "; ".join(errors))
except Exception as e:
    print("EXCEPTION", repr(e))
    await page.screenshot(path=".screenshots/iter52_exception.jpg", quality=20, full_page=False)
print(f"SUMMARY {sum(1 for _, o in results if o)}/{len(results)} passed; S={ {k: v for k, v in S.items() if k != 'att'} }")
