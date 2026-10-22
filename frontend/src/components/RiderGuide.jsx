import { CheckCircle2, ClipboardCheck, ShoppingCart, Sun } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";

const GuideStep = ({ icon: Icon, title, children }) => (
  <div className="flex gap-3">
    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
      <Icon className="h-4 w-4" />
    </span>
    <div>
      <p className="text-sm font-semibold">{title}</p>
      <p className="text-xs leading-5 text-muted-foreground">{children}</p>
    </div>
  </div>
);

export default function RiderGuide({ open, onClose }) {
  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent data-testid="rider-guide-dialog" className="w-[92vw] max-w-md">
        <DialogHeader>
          <p className="eyebrow">Panduan Rider Baru</p>
          <DialogTitle>Siap berjualan dalam 3 langkah</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <GuideStep icon={ClipboardCheck} title="1. Verifikasi stock awal">
            Buka menu Stock Awal, cek jumlah yang diterima, lalu unggah foto verifikasi.
          </GuideStep>
          <GuideStep icon={Sun} title="2. Absen sebelum mulai">
            Di POS, tekan Absen dan gunakan PIN pribadi serta foto bukti kehadiran.
          </GuideStep>
          <GuideStep icon={ShoppingCart} title="3. Catat setiap pesanan">
            Buka POS dengan PIN, pilih produk dan pembayaran. Tutup EOD setelah selesai berjualan.
          </GuideStep>
        </div>
        <button data-testid="rider-guide-complete" onClick={onClose} className="btn-primary h-11 w-full">
          <CheckCircle2 className="h-4 w-4" />Saya mengerti
        </button>
      </DialogContent>
    </Dialog>
  );
}