# SI FOUR AM — PRD

## Original problem statement
Advanced coffee-cart business OS (POS, inventory w/ recipes, menu stock, rider stock & photo evidence, deposits with receipt + WhatsApp, invoices, rider dashboard, main dashboard w/ charts + live rider GPS, cash handover, financial report, salary/incentive tiers, profile, settings dark/light + EN/ID). Roles: Superadmin, Bar Team, Rider. 12 seeded accounts. Desktop sidebar / mobile bottom nav. Orange accents, gold gradient borders, black/white backgrounds.

## User choices
- Maps: Leaflet/OpenStreetMap now (Google Maps later when key provided)
- Full-stack React + FastAPI + MongoDB (not single index.html)
- Photos: user asked for Google Drive → requires Google Cloud OAuth Client ID/Secret (not provided). Currently stored as compressed base64 JPEG in MongoDB.
- WhatsApp: wa.me link + auto-download receipt PNG

## Architecture
- backend/server.py (FastAPI, JWT bearer auth, bcrypt, role deps STAFF/SUPER/ANY), backend/seed.py (accounts, materials, recipes)
- Collections: users, materials, menus, inventory_tx, menu_stock_tx, attendance (unique rider+date), rider_stock (upsert rider+date), sales, customers, deposits (upsert rider+date), invoices, expenses, handovers, gps, login_attempts
- Revenue source of truth per (rider, date): deposit if exists, else POS sales (daily_summaries)
- frontend/src: context/AuthContext, lib/{api,helpers,i18n}, components/{Layout,common,GpsMap}, pages/*

## Implemented (2026-06)
- Auth: login by username/email + password, remember me, PIN gate for POS, change password/PIN, brute-force lockout
- Inventory: materials, IN/OUT/opname tx, recipes + HPP/margin, WA Stock + WA Order Items (with PDF via jsPDF)
- Menu Stock: production deducts recipe + packaging, adjust, superadmin add/edit menu + photo
- POS: attendance check-in/out with photo + PIN (once/day), product grid from rider stock, cart, cash/QRIS, change, receipt (PNG + WA to customer wa.me/62), EOD report, sales history w/ est. profit, loyalty points
- Rider Stock: table with qty dropdowns (0–30, Kopsu Aren 0–50), photo, save → deducts central menu stock, downloads photo, opens WA
- Deposit: PIC auto, rider, date, stock prefilled, remaining/cash/qris/wastage dropdowns, diff → new debt, debt tracking, expenses, net cash, receipt popup auto-screenshot + WA with motivational text
- Invoice (superadmin): customer + WA, rows, discount, invoice no, receipt + WA
- Rider Dashboard: rider select/all, filters (today/yesterday/week/month 16→15/prev/custom), profile, gross, cups, attendance, tier progress (all riders = nearest × count), daily chart, best-selling pie, stock photo history, sales history
- Main Dashboard: KPIs, rider revenue chart, money in/out chart, rider table → Leaflet GPS map of riders on duty (polls 20s; rider browser posts GPS every 30s)
- Cash Handover, Financial Report (ledger w/ running cash/bank balance, COGS, gross/net profit, inventory value, manual expense/income), Salary (allowance Rp20k >20 cups/day, Bronze/Silver/Gold/Platinum with 25-day rule)
- Profile, Settings (theme, EN/ID, notifications, GPS mode, permissions list), role-based nav + More hub

## Revision 1 (2026-06) — implemented
- Mobile-app UX: role-based bottom nav (superadmin 4 + "More" upward menu; barteam 6; rider 3), profile only top-right, desktop sidebar flat; Indonesian default language + expanded dictionary (receipts translated)
- Rider Stock: photo mandatory, PIC auto, new WA report format with time; Deposit: PIC auto, price under name, EOD prefill (requires POS "End Today's Sales" close), Bundling 1/2 (4/10 cups of Rp12k menus → 45k/110k) with menu picker, commission Rp20k, receipt date+time, Web Share API with image
- POS: locked without rider stock / after EOD close / after deposit; bundling buttons; customer lookup by 5-digit phone prefix; sales history table + receipt resend; client_id idempotency
- Invoice: PAID/UNPAID, down payment, remaining payment (bold), pay endpoint, unpaid lookup by phone prefix
- Cash Handover: period filter → expected cash from deposits, unlimited expense lines saved to expenses/finance, difference calc, history + detail dialog
- Rider Dashboard: Total Income (20k×days + incentive), Daily Attendance + Incentive withdraw dialogs (cash/bank, balance check, history), line chart cash+qris, PDF/print
- Salary: no 20-cup rule; click rider → dashboard. Finance: Excel/PDF/WA export, purchase item + material names, withdrawals in ledger
- Inventory: recipes include packaging (migration), PDF Excel-style with time, purchased item/supplier on IN
- Google Sheets/Drive sync via Apps Script (google-apps-script/Code.gs + README), URL configurable in Settings (superadmin) or GOOGLE_APPS_SCRIPT_URL env. NOT active until user deploys and pastes URL.

## Revision 2 (2026-06) — implemented
- Responsive tables fit one screen 320–1920px (compact .qty selects, hide-xs/hide-sm columns, sold/diff inline on phones)
- Customers & loyalty page (/customers, superadmin More) with WA voucher; POS daily target progress (50 cups); Bluetooth thermal print button (Web Bluetooth ESC/POS) in receipts; AI stock forecast (GET /forecast) on Rider Stock
- AI Sales Coach (gpt-5.4-mini via Emergent key, POST /coach/chat): rider GPS → OpenStreetMap Overpass POIs (3 mirrors) + Nominatim area → coaching reply; floating chat for riders; history in coach_chats
- GPS mandatory gate for riders (GpsGate); withdrawals create superadmin notifications (bell in header) + withdrawal receipt with WA to superadmin; rider bank account (22 Indonesian banks dropdown) in Profile

## Revision 3 (2026-06) — File & media storage
- Emergent Object Storage integrated (server.py: init_storage/put_object/get_object/store_photo). All uploaded photos (attendance check-in/out, rider stock evidence, profile, menu) are uploaded to bucket path `sifouram/{folder}/{user_id}/{uuid}.ext`, referenced in `db.files` (soft-delete), and served via GET /api/files/{path} (public by unguessable UUID path, cached). Falls back to inline base64 if storage fails. GET /api/files (staff list), DELETE /api/files/{path} (superadmin soft-delete).

## Revision 4 (2026-06) — 3 new features (tested: iteration_3.json, backend 7/7 + frontend 100%)
- AI "Tanya AI" button restyled as WhatsApp Meta-AI gradient pill (CoachChat.jsx), moved OUT of global Layout → now mounted only inside POS/Kasir page, and only for Rider + Superadmin (Bar Team excluded). Focus: recommend crowded selling spots (existing Overpass POIs).
- Withdrawal disbursement status: create_withdrawal sets status='pending'; new POST /api/withdrawals/{wid}/accept (superadmin, idempotent) → status='diterima' + accepted_by/accepted_at. Salary/Gaji page shows per-rider "Pencairan Gaji / Insentif" list with 'Diterima' button (superadmin only) → flips to 'Diterima ✓'; rider sees 'Pending' badge only.
- Profile: riders can save up to 3 bank accounts (banks[] each {bank_name, bank_account, bank_holder}); UI add/remove rows (cap 3), server also caps to 3. WithdrawDialog lets rider pick target bank (withdraw-bank). Legacy single-bank fields auto-migrated into banks[] on read.

## Revision 5 (2026-06) — batch of 6 UX + data changes (tested: iteration_5.json, 100%)
- No horizontal shift on any device: html/body/#root overflow-x hidden; NotifBell dropdown re-centered with `left-0 right-0 mx-auto` (fade-up's transform:none was cancelling -translate-x-1/2).
- Orientation lock: full-screen `.rotate-lock` overlay (App.js, data-testid rotate-lock) shows in landscape ≤900px, forcing portrait use.
- Tanya AI (Kasir): manual input answers ANY question (broadened backend prompt); coach overlay z-[60] so it clears bottom nav on mobile.
- Bottom nav shrunk ~25% (icons 15px, labels 8px).
- All page/tab TITLE texts removed — PageHeader now renders only action children (no eyebrow/h1).
- One-time data wipe (backend/wipe_tx.py): emptied sales, deposits, rider_stock, eod, handovers, expenses, invoices, customers, inventory_tx, menu_stock_tx, notifications; reset materials.stock & menus.stock to 0 (item/menu definitions kept).

## Revision 6 (2026-06) — 4 UX + i18n/appearance changes (tested: iteration_6.json, frontend 100%)
- Date filter now single horizontal row, smaller buttons (h-7), horizontally scrollable (no wrap).
- Tanya AI upgraded: LINE-style bubbles (user green right / AI left with avatar), WebAudio pop/bubble sound on reply, scroll holds at start of last message, history persists across open/close, manual box answers any question.
- Global appearance controls in Settings > "Teks & Font" (lib/appearance.js): text size A-/A+ (--font-scale), bold toggle (body.app-bold), text color picker (overrides --foreground via hexToHsl), font-type from 12 Google fonts incl. Oswald(Athletic) & Noto Sans Javanese; persisted in localStorage, applied app-wide on load (App.js).
- Languages expanded to 5: ID, EN, 日本語, 中文, العربية (Arabic sets dir=rtl). i18n dict en/id/ja/zh/ar.

## Revision 7 (2026-06) — 9 UX/data changes (tested: iteration_7.json, backend 6/6, frontend 6/7)
- Text-size now scales header + footer too (px→rem in Layout); range clamped 50%–150%.
- Leftover data reset to 0: deleted remaining withdrawals/expenses → finance income/outgo/net/cash/bank all 0; Muhammad Zulfikar no longer -20.000.
- Rekening Utama: banks[] gains `primary` flag (Profile bank-primary-{i}); WithdrawDialog defaults to primary bank.
- Header auto-hides on scroll down / shows on scroll up (Layout hideHead + window scroll).
- Superadmin can change rider photo from Salary tab (salary-photo-{id} → PUT /users/{id}/photo, superadmin-gated).
- Notifications: iPhone-style WebAudio tri-tone on new unread; new 'order' notification when an invoice is created (create_invoice).
- Kasir AI chat user bubble green(#06C755) → orange (bg-primary).
- JA/ZH/AR dictionaries complete for all t() keys.

## Backlog / P1-P2
- Google Drive photo storage (needs OAuth credentials) · Google Maps (needs API key)
- V2: AI demand forecasting, Bluetooth thermal printing, WA auto-broadcast marketing
- Customers/loyalty page UI (data already stored)
- Push notifications

## Final Revision (2026-10) — in progress pending Supabase credentials
- Logo utama diganti memakai aset SI FOUR AM pada login, PIN, dan navigasi. Light mode memakai teks
  hitam; dark mode memakai teks putih. Kontrol warna dan skala teks dihapus; bahasa kini dropdown.
- Role lama dimigrasikan ke Owner/Admin/Bar Team/Rider. Seed dan database aktif hanya menyisakan
  Owner `baa` / Baazulfikar. Owner dapat membuat, mengubah role, serta mengaktifkan/nonaktifkan akun.
- Autentikasi diganti menjadi identifikasi (email/username/WhatsApp) lalu PIN enam angka. Persetujuan
  Syarat & Ketentuan dan Kebijakan Privasi wajib dibaca sampai akhir dan dicatat bersama versinya.
- Reset yang disetujui telah menghapus chat AI, data finansial operasional, transaksi stok, stok rider,
  GPS/absen orphan; stok menu dan bahan disetel nol. Master menu/bahan tetap ada.
- Dashboard Owner menampilkan lima rider teratas dan donut produk; GPS hanya dikirim saat rider absen.
  Dashboard rider memiliki filter minggu lalu dan kartu rank Herald/Warriors/Masters/Divine/Immortal.
- Rider menerima notifikasi motivasi setelah status tugas aktif dan setiap tiga jam saat aplikasi terbuka.
  Preferensi Umum/Muslim tersedia di Pengaturan; kutipan Muslim menggunakan referensi Al-Qur'an,
  sedangkan kutipan umum memakai sumber pidato Steve Jobs yang dapat ditelusuri.
- Revisi navigasi terbaru: logo crest orange, seluruh aksen gold diganti orange, border avatar dan
  inisial hitam, serta pilihan mode Web/Tablet/Mobile dihapus. Tab kategori sticky berada tepat di
  bawah header, dapat digeser horizontal dengan swipe/momentum/keyboard focus, dan memprioritaskan
  tiga tab awal pada mobile. Seluruh sub-tab laporan memakai perilaku horizontal yang sama.
- Laporan Owner diperluas dengan tab Waste, Nilai Persediaan, Pembelian, dan Stok Opname berbasis
  koleksi transaksi sebenarnya, termasuk Excel/PDF/cetak dan empty state. Inventory tetap berupa
  snapshot saat ini, sehingga filter tanggal sengaja tidak ditampilkan pada tab tersebut.
- Info Pengguna kini mendukung foto akun inline dari galeri, maksimal 2 MB; foto dapat dihapus.
  Pembuatan akun juga menyimpan maksimal tiga rekening bank.
- Halaman Laporan Owner baru (`/reports`) memakai transaksi aktual untuk kartu ringkasan, grafik,
  tabel produk, filter pembayaran/tipe order, Excel, PDF A4, dan cetak PDF.
- Supabase: `supabase/001_initial_schema.sql`, `.env.example`, dan `SUPABASE_SETUP.md` telah dibuat.
  CUTOVER DATABASE BELUM DILAKUKAN karena Transaction Pooler URI belum diberikan pengguna.

## Testing (2026-10)
- Iteration 9: 20/20 backend checks pass, browser login and reports passed, desktop/mobile overflow
  checks passed. Follow-up fixes applied for permission scope, CORS, print flow, mobile PIN sizing,
  reports loading/error state, and orphan GPS/attendance cleanup.
- Iteration 11: 13/13 backend checks pass; kategori Desktop/Mobile, enam tab laporan, foto inline,
  dan route hak akses Owner lulus. Semua temuan minor diperbaiki dan diverifikasi dengan build/API.

## Operational Navigation Batch (2026-10) — In Progress
- Bottom navigation Lainnya kembali membuka panel ke atas berisi seluruh tab Lainnya.
- Target Bronze/Silver/Gold/Platinum telah diganti di backend menjadi Herald/Warriors/Masters/Divine/Immortal.
- POS sekarang dibatasi untuk Owner dan Rider; loading menggunakan logo SI FOUR AM beranimasi.
- Stock awal Rider sekarang memerlukan verifikasi Rider sebelum stock dapat dipakai POS. Tampilan Pengambilan Rider dan endpoint verifikasi sudah dibuat.
- Kategori Inventory diganti menjadi Stock. Dropdown Stock untuk Owner/Admin/Bar Team kini memuat Stock Awal, Stock Rider, Pengambilan, Sisa, dan Stock Menu Production; Owner dapat membuka seluruh tab Rider dalam mode baca.
- Tombol Add Menu pada Stock Menu Production dipindahkan dari header ke area Recipes.
- Kartu resep Inventaris kini ringkas secara default; rincian bahan dan quantity hanya muncul saat kartu resep diklik.
- Tab kategori sekarang mendukung swipe mobile, scrollbar horizontal tersembunyi, keyboard focus, serta roda mouse/trackpad untuk menggeser tab ke kanan atau kiri.
- Ikon POS pada bottom navigation diperbesar sekitar 30%, ditempatkan dalam tombol bulat berlatar orange, dan memakai ikon hitam agar jelas terlihat.
- Pada mobile, bar tab tepat di bawah header disembunyikan saat kategori Lainnya aktif karena seluruh navigasi Lainnya telah tersedia melalui panel bottom navigation yang muncul ke atas.
- Kategori Stock dinamai ulang menjadi Inventory dan ikon Inventory dipindahkan ke posisi setelah POS serta sebelum Lainnya pada bottom navigation Owner, Admin, dan Bar Team.
- Tombol Laporan Stok dan Pesan Barang pada halaman Inventaris kini berada dalam satu grup di sisi kiri, dengan urutan Laporan Stok lalu Pesan Barang.
- Logo pada header mobile diperbesar sekitar 30%, dan tombol Pesan Barang di Inventaris kini memakai label PO.
- Bar tab kategori tepat di bawah header telah diganti menjadi dropdown halaman agar daftar pilihan tetap ringkas di setiap ukuran layar.
- Komponen filter periode global kini memakai lebar penuh yang sejajar dengan grid tanggal mulai dan tanggal akhir di bawahnya.
- Halaman Laporan menghapus judul besar dan mengganti deretan tombol jenis laporan dengan satu dropdown pemilih laporan.
- Dropdown jenis laporan dipisahkan ke baris paling atas; filter pembayaran, tipe order, periode, serta ekspor berada di baris bawahnya.
- Urutan terbaru bottom navigation Owner, Admin, dan Bar Team menempatkan Inventory setelah Dashboard dan sebelum POS.
- Bottom navigation kembali menampilkan label untuk seluruh kategori kecuali POS, yang dipertahankan sebagai tombol ikon orange tanpa teks.
- Inventory diposisikan kembali setelah POS dan sebelum Lainnya pada bottom navigation. Header mobile menampilkan role akun aktif di bawah judul SI FOUR AM.
- Label Indonesia untuk Dasbor Utama diperbarui menjadi Dashboard pada navigasi bawah dan seluruh penggunaan terjemahan terkait.
- Bug-fix RiderStock: dependensi hook diperbaiki memakai `useCallback`, pemanggilan API stock/menus menangani error, prediksi stok menangani kegagalan API dengan toast, dan label riwayat diperbaiki menjadi Riwayat Stock.
- Pemilih jenis laporan pada laporan operasional (Waste, Persediaan, Pembelian, Opname) kini menggunakan dropdown, bukan deretan tombol.
- Login perangkat: identifier terakhir diingat secara lokal, persetujuan legal hanya ditampilkan sekali per perangkat, digit PIN tampil satu detik lalu tersamarkan, persetujuan dihapus dari halaman PIN, dan sesi otomatis logout setelah 10 menit tanpa aktivitas.
- Auth/navigation retest Iteration 15: 100% frontend dan backend lulus. Nama akun pada toast sambutan sekarang orange, stale session dihapus saat reload, Bar Team tidak lagi mengalami redirect loop, dan navigasi Admin/Bar Team tidak lagi menautkan POS terlarang.
- Navigasi lanjutan: bottom navigation Stock sekarang langsung menuju Rider Stock/Stock Awal, sementara Production menuju Inventaris dan Stock Menu Production sehingga kategori tidak lagi saling tertukar.
- Dashboard POS baru (`/pos-dashboard`) menampilkan filter periode, Total Tunai, QRIS, Total Penjualan, dan history transaksi dari API penjualan aktual. Iteration 16 lulus 18/18 backend checks dan 100% frontend checks; loading/error/empty state ditambahkan setelah review.
- Iteration 12: 7/7 backend checks lulus, build frontend tanpa lint warning/error, serta Owner login/dashboard/Stock Awal smoke test lulus. Follow-up error handling prediksi telah diterapkan dan build ulang bersih.
- Remaining: Dashboard POS, tab Stock Awal/Sisa dengan filter penuh, Purchase Order + notifikasi, akun pembayaran Owner, serta perubahan keranjang POS sesuai referensi.

## POS P0 Completion (2026-10)
- Rider dashboard salary fix verified in iteration 17: `/api/salary` serializes rank tiers safely,
  uses Herald/Warriors/Masters/Divine/Immortal consistently for commission, and Rider Dashboard
  now has loading, error/retry, and zero-rider empty states.
- POS Keranjang now records `dine_in`, `takeaway`, or `online` orders. Dine In requires a table,
  split payment records separate cash/QRIS amounts, and receipts, EOD, finance summaries, sales
  reports, and Rider rank calculations preserve split totals without duplication.
- POS keeps the menu grid visible while rider stock awaits verification, but blocks product additions
  and payment. Attendance requires a numeric six-digit Rider PIN and photo before check-in.
- Iteration 18: 16/16 backend checks passed plus desktop/mobile POS checks. Follow-up fixes added
  whole-number EOD cup allocation, split-aware POS history, service-type reporting, localized
  attendance errors, PIN-gate throttling, distinct test IDs, accessible receipt dialogs, and clear
  pending-verification copy.
- Remaining P1: complete Stock Awal/Sisa filters and photo-proof Pengambilan workflow; then build
  Production Purchase Order approval/notification flow. P2 remains Broadcast WhatsApp, Owner
  payment accounts, AI stock prediction, and Bluetooth receipt printing.

## Stock P1 Completion (2026-10)
- Pengambilan Rider now requires a Rider acceptance photo before verification. The API validates
  image payloads, stores verification metadata/photo, scopes POS stock to its owning Rider, and
  re-locks POS whenever Owner revises a verified stock handoff.
- Stock Sisa is available for Owner/Admin/Bar Team and Rider, showing initial, sold, and remaining
  quantities. Pending handoffs are clearly marked and retain internally consistent totals.
- Iteration 19 stock verification test suite now passes 13/13 after follow-up fixes; production
  build succeeds. QA stock, sales, Rider accounts, and test files were cleaned back to baseline.
- Next P1: Production Purchase Order request, Owner/Admin approval, and approval notifications.

## Production and More Foundation (2026-10) — In Progress
- Backend endpoints added for Purchase Order creation/listing and Owner/Admin approve/reject decisions,
  including recipient notifications. Owner-only broadcast creates in-app notifications for selected
  role groups, and payment-account endpoints support bank/QRIS account records.
- Backend syntax validation passed. Frontend screens/routes for PO, broadcast WhatsApp links, and
  Owner payment accounts are still pending and must be completed plus end-to-end tested next.

## Production, Broadcast, and Payment Accounts (2026-10)
- Added Production Purchase Order page for Bar Team/Admin/Owner, with material request, Owner/Admin
  approval or rejection, and recipient notifications. New PO notifications now reach both Owner and Admin.
- Added Owner Broadcast page: role selection, in-app notifications, prefilled WhatsApp links, and
  recipient list. Added Owner payment-account page with QRIS image upload.
- Active QRIS accounts are exposed through a safe public endpoint and shown in Rider/Owner POS when
  QRIS payment is selected. Iteration 20 validated end-to-end flows at 14/15 before the final Admin
  notification fix; backend and frontend builds pass after that fix.
- Remaining polish: payment-account edit/deactivate controls, localized navigation labels, decision
  note field, and QRIS modal/enlarged scan treatment on mobile.

## Rider Weekly Rank Target Refresh (2026-10)
- Replaced legacy Rider targets with weekly Herald, Warriors, Masters, Divine, and Immortal brackets:
  Rp20k/0%, Rp30k/5%, Rp35k/7%, Rp40k/10%, and Rp50k/15% attendance/sales benefits respectively.
- Rider dashboard shows uploaded rank artwork, live total commission, and next-rank progress. Clicking
  the rank card now opens Target Rank Rider for both Owner and Rider accounts.
- Fixed rank filters to persist while data reloads, fixed Sunday ISO-style Monday-to-Sunday ranges,
  added full minimum–maximum rank ranges, rider query focus, and localized rank labels.
- Verification: rank API boundary/commission suite 11/11 passed; frontend production build passed.

## Weekly Reset, EOD Session, and Book Period (2026-10)
- Rider rank data is scoped to Monday–Sunday and a timezone-aware Monday 00:00 WIB cron records each
  weekly reset. The cron endpoint is idempotent and verified with a successful authenticated call.
- Removed the ten-minute idle logout. A three-hour idle timer begins only after daily EOD closing; any
  activity after closing renews that three-hour timer.
- Company book period remains 16th through 15th through the shared period helper. QRIS preview state
  is restored in POS to prevent the reported runtime error.
- Follow-up QA fixed bodyless cron delivery and strict Bearer authorization. Rank cards now always use
  Monday–Sunday independently of history filters; backend restart, bodyless cron call, and frontend
  production build passed.

## Navigation and Visual Polish (2026-10)
- Header tab navigation now auto-hides after three seconds with a left-slide animation, collapses to a
  40px area, and can be revealed through a centered `>` action.
- Shared Bento cards use an orange gradient border. Report actions, WhatsApp summaries, compact mobile
  filters, and split report payment/order/service cards have also been added during visual refinements.
- Scrollable report and stock tables use the gradient border on the inner table that actually moves,
  while their outer Bento wrapper remains neutral. QA iteration 27 verified scrolling, WA summaries,
  and empty states; the final mobile Products empty-state width was also fixed and smoke-tested.
- Notification items now route to their matching operational tabs, while incoming Broadcast messages
  open a responsive detail dialog. QA iteration 28 passed 14/14 notification routing and popup checks.
- Report table headers are centered for visual consistency; Settings permission keys are unique and
  message dialogs retain mobile side margins.

## Rider Live Target Detail (2026-10)
- Target Rank Rider now includes a live sales detail panel for all active Riders, showing gross sales,
  current/next rank, and target progress. Data refreshes every 30 seconds while the page is visible.
- Each rank card opens its detailed weekly target, attendance benefit, and sales bonus section; mobile
  card text uses compact currency so target and benefit information remain within two lines.
- Inactive Rider accounts are excluded from salary/live-target queries. Backend rank test suite passed 4/4;
  frontend production build passed.
- The live panel is labeled “Data Rider dengan Target yang Sedang Tercapai” and explicitly shows each
  Rider's achieved rank plus the next target when one is available.
- Header navigation auto-hide pauses while either tab dropdown is focused/open, then resumes its three
  second countdown after the selection is finished.
- POS Dashboard payment summary now shows Total Penjualan as the first full-width card, followed by
  Total Tunai and Total QRIS side-by-side.

## Finalization, Security, and Reset (2026-10)
- Deposit Setoran now keeps manual Stock, Cash, QRIS, Sisa, and Wastage quantities mutually bounded;
  mobile Terjual and Selisih are presented on separate lines. Server-side deposit accounting rejects
  over-counted stock, writes wastage idempotently, and prevents duplicate owner notifications.
- Sales and Product reports now include payment/order/service/Rider filters, KPIs, localized chart
  legends, revenue/HPP/profit/contribution metrics, transaction detail, and complete Excel/PDF exports.
  Payment-filter reports use proportional cup, revenue, and HPP allocation for split payments.
- Security hardening: the frontend uses a Secure HttpOnly session cookie rather than storing new tokens
  in browser storage; sessions are server-revocable, active role/state is read on each request, and
  credential/role/status changes revoke sessions. Added security headers, 5 MB API payload limit,
  rate limiting and lockouts, audit logging without secrets, role denial auditing, and restrictive CORS.
- Validation/security safeguards now reject negative/zero sales and bundle quantities, negative invoice
  amounts, overpayment, stock handoffs above central stock, cross-Rider EOD/debt reads, and re-use atomic
  counters for receipt, invoice, and deposit identifiers.
- Final test results: security/core flow suite 27/27 passed; Setoran/Invoice and Reports regression
  suites 27/27 passed; frontend production build and mobile Owner smoke tests passed.
- Approved operational reset executed: retained only Owner `baa` / `baazulfikar@gmail.com` and master
  menu/material records. Cleared sales, EOD, stock handoffs, deposits, invoices, customers, attendance,
  GPS, notifications, AI chats, purchase orders, broadcasts, payment accounts, sessions, operational
  transactions, and counters. Menu/material stock are set to zero; the audit log retains one reset event.

## Remaining Backlog
- P2: physical Web Bluetooth receipt pairing remains hardware-dependent and is mocked in headless tests.
- Optional future: split the oversized backend into dedicated auth, sales, deposit, and report routers.

## Feature Added — Owner Onboarding Rider Pertama (2026-10)
- Owner Dashboard shows a three-step setup checklist only after the first active Rider is created:
  create stock awal, Rider verification with photo, then POS readiness. The checklist action opens
  Stock Awal and it remains responsive at mobile width.
- The Owner-only `/api/onboarding/owner` status endpoint is RBAC-protected. Onboarding completion is
  stored after that first Rider verifies stock, preventing the checklist from returning daily or when
  that Rider is later deactivated.
- QA passed 8/8 across API RBAC, first-Rider targeting, stock state, Rider verification, POS readiness,
  desktop/mobile rendering, and navigation. The approved operational reset was rerun after QA: one
  Owner remains, all operational collections and stock quantities are zero, and onboarding is ready.

## Features Added — Rider Guide and Web Bluetooth Printing (2026-10)
- Rider login now presents a concise three-step guide before PIN entry on a new browser/device: verify
  stock awal, complete attendance, then use POS and close EOD. The guide can always be reopened from
  the Rider PIN screen and has a mobile-sized tap target.
- Settings now includes a Web Bluetooth ESC/POS thermal printer panel with connection status, connect or
  change-printer flow, test print, disconnect, and a safe unsupported-browser state. Receipt print
  reuses the active printer session and prevents duplicate same-tick print submissions.
- Bluetooth write flow selects the characteristic-supported response mode, sends compatible 20-byte BLE
  chunks, keeps a new printer connection safe from stale old-device disconnect events, and preserves the
  existing printer when a replacement chooser is cancelled.
- QA: Rider-guide/auth suite passed 6/6; mocked browser Bluetooth QA validated connect, change printer,
  test print, receipt print, disconnect, cancellation, and mobile fallback. PHYSICAL PRINTER PAIRING IS
  STILL MOCKED: verify it with the actual 58 mm BLE printer using Chrome on Android/desktop.

## UX Update — Automatic PIN Login (2026-10)
- Login submits automatically immediately after the sixth valid PIN digit is entered or a complete PIN is
  pasted. A ref-based submit guard prevents concurrent duplicate login calls; incorrect PIN behavior
  remains unchanged.
- Verified on mobile Owner login without pressing the Continue button; frontend production build passed.

## UX Update — Active Mobile Navigation (2026-10)
- Bottom navigation now derives its active state from the containing category, so Dashboard, Stock, POS,
  and Production stay orange while any of their tabs or subtabs is open. This overrides inactive dark-mode
  text while retaining the POS action treatment.
- Verified on mobile from the Produk report subtab: the Dashboard navigation item stayed orange.

## Bug Fix — Invalid Session on Stock Remaining (2026-10)
- Root cause: the protected `/rider-stock/remaining` request received HTTP 401 when its HttpOnly cookie
  no longer had a matching server-side session (for example after an approved session reset, logout, or
  session revocation). The Stock Remaining catch handler then showed the raw session error toast.
- Axios now broadcasts unauthenticated API responses to AuthContext, which clears local session state and
  returns the user to Login. The Stock Remaining tab suppresses the redundant 401 toast. Verified by
  revoking a session and opening the remaining-stock route on mobile: Login appeared cleanly.

## Feature Added — Coach Sessions and Contextual Info (2026-10)
- CoachChat now has Gemini-style per-user sessions: New Chat, session history, select, rename-capable API,
  delete, and independent message context. Ownership checks prevent cross-user reads, edits, deletes, and
  LLM context leakage. An automatically created empty session is removed if the LLM fails.
- A global floating Info button appears above the active navigation and opens route-aware help for Sisa
  Stock, Sales/Product reports, POS, Deposit, Inventory, and Stock Rider. Coach remains on the left;
  Info stays on the right and both clear the mobile bottom navigation.
- QA passed chat-session backend regression 9/9 and previous frontend session/info flows. Active-session
  deletion now remains a true blank New Chat; desktop Coach is offset from the sidebar. The final reset
  confirmed one Owner, zero sessions, zero coach sessions, and zero coach messages.

## Feature Added — Fixed Session Policy and Targeted Realtime (2026-10)
- Automatic logout now follows server-issued `session_ends_at`: Owner/Admin/Bar Team expire at the next
  00:00 WIB; Rider expires four hours after EOD. The Rider deadline persists across midnight when a
  previous EOD window is still active, cannot be extended by closing EOD again, and blocks relogin after
  the current-day deadline passes.
- MongoDB-backed `app_revision` drives six-second cross-client refreshes. A LiveData context updates
  Dashboard, Menu Stock, Invoice, and POS without remounting routes, preserving unsaved forms, carts, and
  receipt dialogs. GPS and notification-read events are excluded from refresh noise.
- Dashboard now contains Stock Center Produk with total cup count and the lowest-stock products. QA
  regression passed 11/11; frontend build passed; reset restored the Owner-only zero-data baseline.

## Next P0 — Procurement and Expense Automation
- Build multi-material purchase orders from selected low-stock materials; Admin review then Owner final
  approval; shipping/received states, received-photo evidence, and WA sharing with the specified recipient.
- Add Purchases subtab with price/payment detail and add manual/photo/digital-proof expense creation using
  Gemini 3.1 Pro Vision extraction with mandatory editable review.

## UX Update — Central Stock Detail (2026-10)
- Dashboard Stock Center Produk remains limited to the four lowest-stock products for fast scanning.
  When more products exist, an explicit detail action opens a scrollable dialog with every product and
  its central cup stock, sorted from lowest to highest.
- Frontend production build passed after this update; the Owner-only zero-data baseline is retained.

## Code Quality Fix — Review Critical Items (2026-10)
- Replaced Rider Dashboard `document.write` printing with a safe print-window DOM construction using a
  cloned table and programmatic style node; no raw HTML interpolation remains.
- Confirmed `i18n.js` contains no API keys or credentials. Authentication tokens are not stored in local
  or session storage; browser storage is only used for non-sensitive UI preferences and cleanup of legacy
  key names. Added diagnostic warnings for prior silent realtime/motivation load failures.
- Memoized Dashboard central-stock sorting and aggregation. Frontend production build and backend Python
  compilation pass after the review fixes.

## UX Update — Rider Rank Commission (2026-10)
- Removed the separate Uang Harian withdrawal button from Rider Dashboard.
- Moved Estimasi Komisi Utama Anda into a readable overlay at the bottom of the Rank card image, directly
  under its commission label. Frontend production build passed.

## UX Update — Rider Bottom Navigation (2026-10)
- Rider mobile bottom navigation now has five direct destinations in the requested order: Dashboard,
  Stock, POS, Akun, and Pengaturan. The Lainnya menu is removed for Rider.
- Rider home now opens Dashboard. POS keeps its highlighted center action while retaining a visible POS
  label. Frontend production build passed.

## UX Update — Rider Rank Card Layout (2026-10)
- Rank Mingguan and rank name now sit above the card image on one row. The commission value is displayed
  at the image's left center in a larger font, without the former dark overlay or commission label.
- Frontend production build passed.

## UX Update — Rider Rank Alignment (2026-10)
- Rank name uses the same eyebrow font/color treatment as Rank Mingguan. The commission overlay moved ten
  percent upward and now spans the image width while preserving its left-aligned value.
- Frontend production build passed.

## UX Update — Rider Rank Progress (2026-10)
- Commission value is now centered vertically in the Rank image with a 20% larger font. Rank progress
  moved into the bottom of the card image. The incentive availability line no longer includes the
  withdrawal arrow.
- Frontend production build passed.

## UX Update — Bar Team POS Navigation (2026-10)
- Tim Bar now has direct POS access in the mobile bottom navigation. The Tim Bar POS category opens POS
  first and retains Deposit as its secondary tab.
- Frontend production build passed.

## UX Update — Bar Team Deposit Access (2026-10)
- Tim Bar mobile bottom navigation now shows Deposit immediately after POS, while retaining the POS category
  tab structure. Frontend production build passed.

## UX Update — Bar Team Primary Deposit Action (2026-10)
- POS was removed from the Bar Team bottom navigation. Deposit is now the highlighted center-style primary
  action with the former POS icon treatment, while Stock, Production, and Settings remain available.
- Frontend production build passed.

## Feature Added — Low Stock Purchase Request Shortcut (2026-10)
- Low Stock status in Inventory is now a clickable action. It routes to Purchase Orders with the selected
  material already prefilled, reducing duplicate manual entry for Bar Team purchase requests.
- Frontend production build passed.

## UX Update — Rider Commission Contrast (2026-10)
- Rider commission text moved upward within the Rank image and now uses a white outline with black shadow
  for legibility over any rank artwork.
- Frontend production build passed.

## UX Update — Rider Rank Position Refinement (2026-10)
- Commission value returned to its prior vertical center position; progress bar moved upward to ten percent
  from the bottom of the Rank image. Frontend production build passed.

## Feature Added — Procurement Approval and Receiving Flow (2026-10)
- Purchase Orders now support multiple materials, supplier, target-arrival date, unit estimate, and creation
  from individual or all low-stock shortcuts. The staged state machine is Admin review → Owner approval →
  shipped → Barang Datang, with role-specific notifications and atomic state guards.
- Confirming Barang Datang requires a validated image proof, records a protected receipt, creates one inventory
  IN transaction per ordered material, and updates stock exactly once using MongoDB `$inc`. Decision notes are
  now preserved per stage instead of overwriting prior review context.
- PO cards can download a local PDF and open a user-reviewed WhatsApp composer for `6281283578212`; the UI
  clearly asks the user to attach the downloaded PDF manually because `wa.me` cannot attach files.
- Verification: backend Procurement QA passed 19/19, frontend production build passed, desktop/mobile smoke
  tests passed, and the WhatsApp popup was verified with the correct recipient. All temporary QA data was
  removed after testing.

## Feature Added — Expense Proof Review Baseline (2026-10)
- Finance now supports manual expense creation with optional receipt/payment proof, editable AI-draft review,
  private proof URLs, and protected ledger access. Invalid/blank/unsupported proofs are rejected.
- Expense QA passed 21/21 and the production build passed. Live Gemini extraction remains blocked because the
  backend's configured Universal Key differs from the managed key and receives a 401; the UI safely keeps the
  editable manual path available and reports the failure without persisting a draft.

## Current Priorities
- P0: Restore the managed Universal Key available to the backend preview/production environment so Gemini 3.1
  Pro Vision receipt extraction can return live drafts.
- P1: Resolve remaining React Hook dependency warnings and finish the planned `server.py` refactor for complex
  sale/deposit functions.
- P2: Improve procurement with partial receiving and supplier-price history after operational validation.

## Integration Update — Gemini Expense and Coach Models (2026-10)
- Receipt extraction now tries Gemini 3.8 Flash first for routine proofs. If the extracted nominal is empty or
  the returned confidence is below 80%, it retries with Gemini 3.1 Pro Preview. The editable expense draft
  identifies the selected model and confidence; no AI result is ever saved automatically.
- CoachChat defaults to Gemini 3.8 Flash for operational conversation, while the existing explicit provider
  selections remain available. Python compilation, parser tests (5/5), and frontend production build passed.
- Live model verification remains pending the managed Universal Key environment refresh; no key was exposed,
  hardcoded, or edited in source control.

## Feature Added — Managed Google Sign-In and Coach Model Selection (2026-10)
- PIN login remains available. The Login page now offers Emergent-managed Google Sign-In and exchanges a
  managed callback session for the existing HttpOnly app cookie only when the verified Google email already
  exists in `users`. The configured Owner email is `baazulfikar@gmail.com`; no self-registration is allowed.
- Google callback requests are rate-limited, single-run in React StrictMode, check verified email and Rider EOD
  expiry, use a background thread for the upstream lookup, and return safe JSON errors for invalid sessions.
- CoachChat now offers Gemini Flash, GPT-5.6 Terra, GPT-5.4, Claude Sonnet 5.5, and Claude Sonnet 4.6 choices.
  QA confirmed PIN/cookie safety and the selector; live Coach replies still await restoration of the managed
  Universal Key, which currently fails upstream with an invalid-key response.

## In Progress — SI FOUR A.M Operational UI Revisions (2026-10)
- Browser title, description, and favicon now use SI FOUR A.M | Coffee Cart Operating System branding.
- Dashboard Stock Center item cells now open the stock-detail dialog on click. Menu production is disabled when
  its recipe materials cannot satisfy the requested production quantity.
- Stock Awal Rider now requires a review dialog before save; saving persists the existing evidence and opens the
  reviewed WhatsApp handoff. Remaining requested work: total stock summary, editable Rank targets, POS payment
  bottom sheet/QRIS confirmation, Admin Deposit entry, and Purchase workspace.


## Feature Change — Bottom Nav Icon Scale & Dummy Account Purge (2026-10-24)
- Layout bottom navigation: non-primary icons scaled from `h-4 w-4` to `h-6 w-6` and the primary FAB icon
  from `h-5 w-5` to `h-[1.875rem] w-[1.875rem]` (+50% visual size per user request). FAB container bumped
  from `h-10 w-10` to `h-12 w-12` to accommodate. `MoreHorizontal` icon matched to `h-6 w-6`.
- Dummy preview accounts (`dummy_owner`, `dummy_admin`, `dummy_barteam`, `dummy_rider`) and every record
  they created were purged via `backend/scripts/cleanup_dummy_accounts.py` — removed 4 users plus 241
  transactional docs (sessions, audit_logs, sales, rider_stock, inventory_tx, menu_stock_tx) and net-reversed
  10 material stocks and 2 menu stocks back to pre-dummy baselines.
- Server-side RBAC bypass (`is_dummy_preview`) in `get_user` + `roles` was removed; only the real Owner
  `baa` (`baazulfikar@gmail.com`) remains and all role gates are strictly enforced again.


## Perbaikan Error POS — Status Absen (2026-10-24)
- Permintaan pengguna: perbaiki `ReferenceError: att is not defined` dan uji ulang POS, termasuk absen sekali serta tombol Tutup Penjualan.
- Akar masalah direproduksi pada browser dengan login Owner asli: komponen POS merujuk state `att` yang hanya didefinisikan di komponen anak Attendance, sehingga seluruh halaman gagal dirender.
- `frontend/src/pages/POS.jsx`: state absen kini dimiliki POS dan dibagikan ke dialog. Status dimuat berdasarkan Rider/tanggal serta revision sinkronisasi, tanpa menunggu dialog dibuka. Respons lama diabaikan saat berganti Rider.
- Setelah check-in berhasil, dialog tertutup, tombol menjadi Sudah Absen/nonaktif dan Tutup Penjualan aktif. Loading/gagal muat menonaktifkan kedua tombol; tersedia Coba lagi. Draft PIN/foto dan keranjang tetap tersimpan selama sinkronisasi.
- Pilihan Rider dipindahkan ke header agar Owner tetap bisa berganti Rider setelah absen; petunjuk halaman disesuaikan. Keranjang dibersihkan hanya setelah EOD berhasil, bukan saat permintaan gagal.
- Pengujian: iteration_52 lulus 46/46 pemeriksaan; iteration_53 lulus 28/28 pemeriksaan terarah (termasuk peran Rider, PIN gate, reload, EOD gagal/sukses). Login dan pembukaan POS Owner memakai API asli. Alur Rider/absen/EOD memakai fixture browser **MOCKED khusus pengujian** agar data operasional tidak berubah; pengujian backend tidak dilakukan pada tugas frontend ini.
- Build frontend akhir berhasil (`yarn build`, `/tmp/pos-build-final.log`); tidak ditemukan error kompilasi. Iteration_54 memastikan kedua skrip regresi berupa modul Python valid dengan `async run(page)`, meneruskan kegagalan pengujian, serta lulus pemeriksaan sintaks/lint tanpa mengubah aplikasi.
- Tidak ada perubahan backend, autentikasi, kredensial, atau integrasi. Tidak membuat akun dummy dan tidak menyimpan transaksi/absen/EOD uji ke database. Skrip regresi: `tests/pos_attendance_regression_iter52.py` dan `tests/pos_attendance_regression_iter53.py`.

### Prioritas Berikutnya (belum dikerjakan dalam perbaikan ini)
- P1: panel Owner untuk menyetujui/menolak permintaan perubahan profil.
- P1: validasi pemetaan baris nota AI pada Purchase dan verifikasi Gemini dengan konfigurasi Universal Key aktif.
- P1: refaktor terencana fungsi backend create_sale, save_deposit, create_invoice; tidak termasuk lingkup perbaikan POS ini.
- P2: penerimaan barang bertahap per bahan dan riwayat harga pemasok.
- Verifikasi pengguna: ukuran ikon navigasi terakhir dan hasil pembersihan akun dummy dari sesi sebelumnya.


## Fitur — Konfirmasi Stock Awal & Unduh Otomatis PDF/Excel (2026-10-24)
- Popup konfirmasi Stock Awal: rincian Rider/PIC/tanggal/item/total + foto bukti; tombol "Kembali & Revisi" dan "Simpan & Kirim WhatsApp" (simpan ke DB lalu bagikan teks + file foto via Web Share; fallback wa.me teks).
- Semua tombol PDF/Excel (Laporan, Operasional, Keuangan, Inventory, Deposit Rider, PO) memakai helper `savePdf`/`saveExcel` (blob + anchor download) → unduh otomatis.
- Fix: foto data-URL dikonversi via atob (CSP memblokir fetch data:). Diuji iteration_55.

