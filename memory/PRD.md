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
