# SI FOUR AM — Panduan Revisi Final

## Isi paket

- `frontend/`: React web app.
- `backend/`: FastAPI API dan MongoDB source aktif.
- `supabase/001_initial_schema.sql`: skema, indeks, dan RLS Supabase.
- `SUPABASE_SETUP.md`: langkah migrasi Supabase yang aman.
- `backend/.env.example` dan `frontend/.env.example`: contoh konfigurasi tanpa rahasia.
- `auth_testing.md`: skenario pengujian autentikasi.

## Menjalankan lokal

1. Salin `backend/.env.example` menjadi `backend/.env`, lalu isi nilai MongoDB, JWT, dan CORS.
2. Salin `frontend/.env.example` menjadi `frontend/.env`, lalu isi URL API.
3. Jalankan `pip install -r backend/requirements.txt`.
4. Jalankan `yarn install` di folder `frontend`.
5. Jalankan backend melalui konfigurasi proses Anda pada port `8001`.
6. Jalankan `yarn start` di folder `frontend` untuk development atau `yarn build` untuk production.

## Akses dan hak pengguna

| Role | Akses utama |
|---|---|
| Owner | Seluruh dashboard, laporan, pengguna, pengaturan, inventori, POS, produksi, GPS, dan administrasi. |
| Admin | Operasional dashboard, stok, POS, produksi, setoran, serta data rider sesuai hak API. |
| Bar Team | Operasional stok, POS, produksi, setoran, serta data rider sesuai hak API. |
| Rider | POS, dashboard dan stok miliknya sendiri. |

Owner membuat akun baru dari **Info Pengguna**. Akun memiliki status aktif/nonaktif, role,
dan PIN enam angka. Login aplikasi menggunakan identitas terdaftar lalu PIN, bukan password.

Rider dapat memilih motivasi umum atau Muslim di Pengaturan. Motivasi tampil saat status tugas
aktif lalu paling cepat setiap tiga jam selama aplikasi terbuka.

Dashboard Owner memiliki laporan Penjualan, Produk, Waste, Nilai Persediaan, Pembelian, dan Stok
Opname. Semua ekspor Excel, PDF, dan cetak memakai data sesuai filter aktif; Nilai Persediaan adalah
snapshot stok saat ini sehingga tidak menggunakan filter tanggal.

## Data yang direset

Atas persetujuan Owner, percakapan AI, pengeluaran, handover, penarikan, transaksi stok,
stok rider, data GPS/absen orphan, dan stok master telah direset. Master bahan dan menu tetap ada
dengan stok nol. Akun legacy telah dihapus dan hanya Owner `baa` yang tersisa.

## Supabase

Skema SQL dan RLS tersedia, namun cutover belum dilakukan karena URI **Transaction Pooler**
Supabase belum diberikan. Ikuti `SUPABASE_SETUP.md` dan lakukan validasi CRUD/RLS sebelum
mengganti sumber database aktif. Jangan pernah menyimpan `DATABASE_URL` atau kredensial Supabase
di frontend.

## Pengujian yang telah dilakukan

- Backend: identifikasi akun, persetujuan dokumen, PIN salah/benar, pemisahan token, Owner API,
  laporan nol pasca-reset, batas rank, dan reset data.
- Frontend: alur login dokumen → PIN, laporan Owner, filter, ekspor Excel/PDF, desktop dan mobile
  tanpa overflow horizontal.
- Build: `yarn build` berhasil tanpa error.

## Konfigurasi eksternal yang masih diperlukan

- URI Transaction Pooler Supabase untuk menjalankan migrasi database produksi.
- Object Storage membutuhkan kredensial integrasi aktif jika ingin unggahan foto disimpan di object
  storage; aplikasi mempertahankan fallback inline bila layanan tidak tersedia.