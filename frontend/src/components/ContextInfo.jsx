import { CircleHelp } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import { useState } from "react";

const pageInfo = (location, category) => {
  const current = `${location.pathname}${location.search}`;
  if (current === "/rider-stock?view=remaining") {
    return {
      title: "Sisa Stock",
      body: "Bandingkan stock awal, cup terjual, sisa fisik, dan selisih setiap Rider pada periode yang dipilih.",
    };
  }
  if (current.startsWith("/reports?view=products")) {
    return {
      title: "Laporan Produk",
      body: "Lihat cup terjual, revenue, HPP, laba, dan kontribusi setiap produk pada periode aktif.",
    };
  }
  if (current.startsWith("/reports")) {
    return {
      title: "Laporan Penjualan",
      body: "Gunakan filter periode, pembayaran, pesanan, layanan, dan Rider untuk membaca transaksi aktual.",
    };
  }
  if (current.startsWith("/deposit")) {
    return {
      title: "Setoran",
      body: "Masukkan stock fisik, Cash, QRIS, Sisa, dan Wastage setelah EOD Rider selesai.",
    };
  }
  if (current.startsWith("/pos")) {
    return {
      title: "POS",
      body: "Pilih Rider yang bertugas, masukkan pesanan serta pembayaran, lalu simpan transaksi secara langsung.",
    };
  }
  if (current.startsWith("/inventory")) {
    return {
      title: "Inventaris",
      body: "Kelola bahan, stock menu, resep, produksi, wastage, dan riwayat inventaris dari satu tempat.",
    };
  }
  if (current.startsWith("/rider-stock")) {
    return {
      title: "Stock Rider",
      body: "Tetapkan stock awal dari pusat, verifikasi penerimaan Rider, dan tinjau riwayat stock harian.",
    };
  }
  return {
    title: category?.name || "Info Halaman",
    body: "Gunakan tab di atas untuk berpindah tampilan dan melihat data operasional sesuai kategori ini.",
  };
};

export default function ContextInfo({ location, category }) {
  const [open, setOpen] = useState(false);
  const info = pageInfo(location, category);
  const isPos = location.pathname === "/pos";

  return (
    <>
      <button
        data-testid="context-info-button"
        onClick={() => setOpen(true)}
        className={`fixed right-4 z-40 flex h-11 w-11 items-center justify-center rounded-full border border-primary/30 bg-card text-primary shadow-lg transition-transform hover:scale-105 active:scale-95 lg:bottom-6 ${isPos ? "bottom-40" : "bottom-24"}`}
        aria-label={`Info ${info.title}`}
      >
        <CircleHelp className="h-5 w-5" />
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="context-info-dialog" className="w-[92vw] max-w-sm">
          <DialogHeader>
            <p className="eyebrow">Info Tab</p>
            <DialogTitle>{info.title}</DialogTitle>
          </DialogHeader>
          <p data-testid="context-info-body" className="text-sm leading-6 text-muted-foreground">
            {info.body}
          </p>
        </DialogContent>
      </Dialog>
    </>
  );
}