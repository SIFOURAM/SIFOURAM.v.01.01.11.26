# Konfigurasi Supabase SI FOUR AM

Migrasi aplikasi belum diaktifkan karena URI Transaction Pooler Supabase belum diberikan.
MongoDB tetap menjadi sumber data aktif sampai koneksi Supabase terverifikasi.

## Yang perlu disiapkan

1. Buat project Supabase dan buka **Connect**.
2. Pilih **Transaction Pooler**, bukan Direct Connection atau Session Pooler.
3. Simpan URI port `6543` ke `DATABASE_URL` backend. Jangan letakkan URI ini di frontend.
4. Jalankan SQL pada `supabase/001_initial_schema.sql` melalui SQL Editor Supabase.
5. Gunakan akun database backend untuk seluruh akses aplikasi. Browser hanya berkomunikasi dengan API FastAPI.

## Keamanan dan RLS

Seluruh tabel mengaktifkan RLS. Kebijakan memakai konteks koneksi `app.user_id` dan `app.role`.
Saat layer PostgreSQL diaktifkan, FastAPI harus mengatur dua nilai ini pada setiap transaksi
sebelum menjalankan query. Rider hanya dapat membaca data miliknya sendiri; Owner, Admin, dan
Bar Team dibatasi sesuai kebijakan pada berkas migrasi.

## Validasi sebelum cutover

- Jalankan pembacaan, pembuatan, pembaruan, dan penghapusan untuk setiap koleksi utama.
- Cocokkan jumlah transaksi dan total penjualan antara MongoDB dan Supabase.
- Uji RLS sebagai Owner, Admin, Bar Team, dan Rider.
- Baru alihkan `DATABASE_URL` aktif setelah seluruh pengujian lolos.