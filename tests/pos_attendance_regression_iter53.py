# Regresi POS iterasi 53 - isi skrip untuk tool browser_automation (objek `page` tersedia).
# Login Owner asli hanya untuk sesi; peran Rider, absensi, stok, on-duty, GPS, PIN dan EOD
# seluruhnya MOCKED lewat fixture browser (page.route) khusus pengujian. Tidak ada data DB diubah.
# Modul valid: jalankan dengan `await run(page)` (Playwright async Page). Gagal -> AssertionError/exception dilempar.
import json, base64, re, os


async def run(page):
    """Jalankan regresi; melempar AssertionError bila ada assertion gagal, exception diteruskan."""
    os.makedirs(".screenshots", exist_ok=True)

    # Ambil URL frontend dari .env dan kredensial Owner dari memory (tidak dicetak)
    def _env(key):
        for ln in open("/app/frontend/.env"):
            if ln.startswith(key + "="): return ln.split("=", 1)[1].strip()
    BASE = _env("REACT_APP_BACKEND_URL").rstrip("/")
    _md = open("/app/memory/test_credentials.md").read()
    _row = [c.strip() for c in re.search(r"^\|\s*owner\s*\|.*$", _md, re.M).group(0).strip("|").split("|")]
    OWNER_ID, OWNER_PIN = _row[1], _row[4]

    PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    FIX_PIN = "246810"  # PIN fixture Rider (bukan PIN asli)
    results, errors = [], []
    def rec(name, ok, extra=""):
        results.append((name, ok)); print(("PASS " if ok else "FAIL ") + name + (" | " + extra if extra else ""))
    page.on("pageerror", lambda e: errors.append(str(e)))

    RIDER = {"id": "fx_rider_self", "name": "FX Rider Self", "username": "fx_rider", "role": "rider", "active": True, "settings": {"gps_mode": "off"}}
    S = {"att": {}, "closed": False, "close_fail": False, "close_posts": 0, "checkin_posts": 0, "pin_posts": 0,
         "sales_posts": 0, "gps_posts": 0, "blocked": [], "rider_mode": False}

    # Fixture: semua respons operasional disajikan dari memori browser
    async def fx(route, request):
        url, m = request.url, request.method
        path = url.split("/api", 1)[1].split("?")[0]
        q = dict(re.findall(r"[?&]([^=&]+)=([^&]*)", url))
        def ok(d, st=200): return route.fulfill(status=st, content_type="application/json", body=json.dumps(d))
        if path == "/auth/me" and S["rider_mode"]: return await ok(RIDER)
        if path == "/auth/verify-pin" and S["rider_mode"]:
            S["pin_posts"] += 1; b = json.loads(request.post_data or "{}")
            return await (ok({"ok": True}) if b.get("pin") == FIX_PIN else ok({"detail": "PIN salah (fixture)"}, 400))  # 400 agar tidak memicu session-expired
        if path == "/users" and q.get("role") == "rider":
            return await ok([{k: RIDER[k] for k in ("id", "name", "role", "active")}])
        if path == "/attendance/on-duty": return await ok({"on_duty": bool(S["att"])})
        if path == "/gps" and m == "POST": S["gps_posts"] += 1; return await ok({"ok": True})
        if path == "/attendance" and m == "GET":
            r = S["att"].get((q.get("rider_id"), q.get("start"))); return await ok([r] if r else [])
        if path == "/attendance/checkin" and m == "POST":
            S["checkin_posts"] += 1; b = json.loads(request.post_data or "{}")
            r = {"id": "fx_att", "rider_id": b["rider_id"], "date": b["date"], "checkin_at": "2026-01-15T08:00:00+07:00", "checkin_time": "08:00"}
            S["att"][(b["rider_id"], b["date"])] = r; return await ok(r)
        if path == "/pos/stock":
            return await ok({"has_stock": True, "closed": S["closed"], "deposited": False,
                             "items": [{"menu_id": "fxm1", "name": "FX Kopi", "price": 15000, "photo": "", "remaining": 5, "stock": 5, "sold": 0, "initial": 5}]})
        if path.startswith("/payment-accounts/public"): return await ok([])
        if path == "/customers/lookup": return await ok({"customers": []})
        eodrow = {"date": q.get("date"), "transactions": 0, "rows": [{"menu_id": "fxm1", "name": "FX Kopi", "initial": 5, "remaining": 5, "cash_qty": 0, "qris_qty": 0}],
                  "total_cups": 0, "total_cash": 0, "total_qris": 0, "total": 0}
        if path == "/sales/eod" and m == "GET": return await ok({**eodrow, "closed": S["closed"]})
        if path == "/sales/eod/close" and m == "POST":
            S["close_posts"] += 1
            if S["close_fail"]: return await ok({"detail": "fixture EOD failure"}, 500)
            S["closed"] = True; return await ok({**eodrow, "closed": True, "session_ends_at": "2026-12-31T23:59:00+07:00"})
        if path == "/sales" and m == "POST": S["sales_posts"] += 1; return await route.abort()
        if m != "GET": S["blocked"].append(m + " " + path); return await route.abort()  # keamanan: mutasi tak dikenal diblokir
        return await route.continue_()

    async def dis(tid): return await page.get_by_test_id(tid).is_disabled()
    async def ready_wait(): await page.wait_for_selector('[data-testid="attendance-loading"]', state="detached", timeout=8000)
    async def cart_text():
        b = page.get_by_test_id("pos-cart-floating-button"); return await b.inner_text() if await b.count() else ""

    try:
        await page.set_viewport_size({"width": 1920, "height": 800})
        tok = (await (await page.request.post(f"{BASE}/api/auth/identify", data={"identifier": OWNER_ID, "terms_accepted": True, "privacy_accepted": True})).json()).get("account_token")
        r2 = await page.request.post(f"{BASE}/api/auth/login", data={"account_token": tok, "pin": OWNER_PIN, "remember": True})
        rec("owner login 200", r2.status == 200)
        await page.context.grant_permissions(["geolocation"], origin=BASE)
        await page.context.set_geolocation({"latitude": -6.2, "longitude": 106.8})
        await page.route("**/api/**", fx)

        # --- A. Owner tanpa Rider: teks notice
        await page.goto(f"{BASE}/pos"); await page.wait_for_selector('[data-testid="pos-page"]', timeout=15000)
        await page.wait_for_timeout(800)
        nt = await page.get_by_test_id("owner-pos-preview").inner_text()
        rec("owner notice meminta pilih Rider", "Pilih Rider" in nt, nt)
        rec("owner notice tidak janji produk tampil tanpa rider", "tanpa" not in nt.lower() and await page.get_by_test_id("product-grid").count() == 0)
        rec("pick-rider-hint tidak tampil untuk owner", await page.get_by_test_id("pick-rider-hint").count() == 0)

        # --- B. Owner+fixture Rider: EOD gagal (500) -> keranjang tetap; EOD sukses -> keranjang hilang & terkunci
        await page.get_by_test_id("pos-rider-select").select_option("fx_rider_self"); await ready_wait()
        await page.get_by_test_id("absen-button").click(); await page.wait_for_selector('[data-testid="absen-dialog"]')
        await page.get_by_test_id("attendance-pin-input").fill("123456")
        await page.locator('[data-testid="absen-dialog"] input[type=file]').set_input_files({"name": "a.png", "mimeType": "image/png", "buffer": PNG})
        await page.wait_for_timeout(600); await page.get_by_test_id("checkin-button").click()
        await page.wait_for_selector('[data-testid="absen-dialog"]', state="detached", timeout=10000)
        await page.get_by_test_id("pos-product-fxm1").click(); await page.get_by_test_id("pos-product-fxm1").click()
        c0 = await cart_text(); rec("cart 30.000 sebelum EOD", "30.000" in c0, c0)
        S["close_fail"] = True
        await page.get_by_test_id("eod-button").click(); await page.wait_for_selector('[data-testid="eod-receipt"]', timeout=8000)
        await page.get_by_test_id("eod-close-button").click(); await page.wait_for_timeout(1200)
        rec("EOD gagal: POST sekali", S["close_posts"] == 1)
        rec("EOD gagal: tombol tutup masih ada", await page.get_by_test_id("eod-close-button").count() == 1)
        await page.keyboard.press("Escape"); await page.wait_for_timeout(600)
        rec("EOD gagal: keranjang tetap", (await cart_text()) == c0, await cart_text())
        rec("EOD gagal: tidak terkunci", await page.get_by_test_id("pos-locked").count() == 0 and not await dis("pos-product-fxm1"))
        await page.get_by_test_id("pos-cart-floating-button").click()
        rec("EOD gagal: payment sheet bisa dibuka", await page.get_by_test_id("pos-payment-sheet").count() == 1)
        await page.get_by_test_id("pos-payment-sheet").click(position={"x": 960, "y": 100}); await page.wait_for_timeout(400)
        S["close_fail"] = False
        await page.get_by_test_id("eod-button").click(); await page.wait_for_selector('[data-testid="eod-receipt"]', timeout=8000)
        await page.get_by_test_id("eod-close-button").click(); await page.wait_for_timeout(1500)
        rec("EOD sukses: POST total 2", S["close_posts"] == 2, str(S["close_posts"]))
        await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
        rec("EOD sukses: floating cart hilang", await page.get_by_test_id("pos-cart-floating-button").count() == 0)
        rec("EOD sukses: payment sheet tidak ada", await page.get_by_test_id("pos-payment-sheet").count() == 0)
        rec("EOD sukses: pos-locked tampil", await page.get_by_test_id("pos-locked").is_visible())
        rec("EOD sukses: produk terkunci", await dis("pos-product-fxm1"))

        # --- C. Peran Rider (MOCKED /auth/me) + PIN gate
        S.update({"att": {}, "closed": False, "close_posts": 0, "checkin_posts": 0, "rider_mode": True})
        await page.evaluate("sessionStorage.removeItem('si4am_pos')")
        await page.goto(f"{BASE}/pos"); await page.wait_for_selector('[data-testid="pin-gate"]', timeout=15000)
        rec("rider: PIN gate tampil", True)
        for k in "111111": await page.get_by_test_id(f"pin-key-{k}").click()
        await page.wait_for_timeout(1000)
        rec("rider: PIN salah tetap di gate", await page.get_by_test_id("pin-gate").count() == 1 and await page.get_by_test_id("pos-page").count() == 0)
        for k in FIX_PIN: await page.get_by_test_id(f"pin-key-{k}").click()
        await page.wait_for_selector('[data-testid="pos-page"]', timeout=8000)
        rec("rider: PIN fixture benar membuka POS", S["pin_posts"] == 2, str(S["pin_posts"]))
        await ready_wait()
        rec("rider: tanpa rider-select", await page.get_by_test_id("pos-rider-select").count() == 0)
        rec("rider: tanpa notice owner/hint", await page.get_by_test_id("owner-pos-preview").count() == 0 and await page.get_by_test_id("pick-rider-hint").count() == 0)
        rec("rider kosong: Absen aktif, EOD nonaktif", (not await dis("absen-button")) and await dis("eod-button"))
        await page.get_by_test_id("absen-button").click(); await page.wait_for_selector('[data-testid="absen-dialog"]')
        await page.get_by_test_id("attendance-pin-input").fill("654321")
        await page.locator('[data-testid="absen-dialog"] input[type=file]').set_input_files({"name": "r.png", "mimeType": "image/png", "buffer": PNG})
        await page.wait_for_timeout(600); await page.get_by_test_id("checkin-button").click()
        await page.wait_for_selector('[data-testid="absen-dialog"]', state="detached", timeout=10000)
        rec("rider: checkin POST sekali", S["checkin_posts"] == 1)
        rec("rider: 'Sudah Absen' nonaktif, EOD aktif", await dis("absen-button") and "Sudah Absen" in await page.get_by_test_id("absen-button").inner_text() and not await dis("eod-button"))
        await page.reload(); await page.wait_for_selector('[data-testid="pos-page"]', timeout=10000); await ready_wait()
        rec("rider reload: PIN gate tidak muncul lagi (sessionStorage)", await page.get_by_test_id("pin-gate").count() == 0)
        rec("rider reload absen ada: Absen nonaktif, EOD aktif", await dis("absen-button") and not await dis("eod-button"))
        await page.get_by_test_id("pos-product-fxm1").click()
        await page.get_by_test_id("eod-button").click(); await page.wait_for_selector('[data-testid="eod-receipt"]', timeout=8000)
        await page.get_by_test_id("eod-close-button").click(); await page.wait_for_timeout(1500)
        await page.keyboard.press("Escape"); await page.wait_for_timeout(800)
        rec("rider EOD sukses: cart hilang + terkunci", await page.get_by_test_id("pos-cart-floating-button").count() == 0 and await page.get_by_test_id("pos-locked").is_visible() and await dis("pos-product-fxm1"))
        rec("tidak ada POST /sales", S["sales_posts"] == 0)
        rec("tidak ada pageerror", not errors, "; ".join(errors))
        S["rider_mode"] = False
        await page.evaluate("sessionStorage.removeItem('si4am_pos')")
        await page.unroute("**/api/**")
    except Exception as e:
        print("EXCEPTION", repr(e))
        try:
            await page.screenshot(path=".screenshots/iter53_exception.jpg", quality=20, full_page=False)
        except Exception:
            pass
        raise
    print(f"SUMMARY {sum(1 for _, o in results if o)}/{len(results)} passed; blocked={S['blocked']} gps_posts={S['gps_posts']}")
    # Gagalkan run bila ada assertion yang gagal
    failed = [n for n, o in results if not o]
    if not results or failed:
        raise AssertionError(f"{len(failed)} assertion gagal: {failed}")
    return results
