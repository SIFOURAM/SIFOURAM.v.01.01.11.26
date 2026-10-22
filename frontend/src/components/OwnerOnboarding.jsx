import { useEffect, useState } from "react";
import { Check, ClipboardList, PackageCheck, Store } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Bento } from "./common";

const Step = ({ done, icon: Icon, title, detail, testId }) => (
  <div className="flex items-start gap-3" data-testid={testId}>
    <span
      className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
        done ? "bg-emerald-500 text-white" : "bg-muted text-primary"
      }`}
    >
      {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
    </span>
    <div>
      <p className="text-sm font-semibold">{title}</p>
      <p className="text-xs text-muted-foreground">{detail}</p>
    </div>
  </div>
);

export default function OwnerOnboarding() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);

  useEffect(() => {
    if (user.role !== "owner") {
      return undefined;
    }
    let active = true;
    const load = () => api.get("/onboarding/owner")
      .then((response) => active && setStatus(response.data))
      .catch(() => active && setStatus(null));
    load();
    const intervalId = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, [user.role]);

  if (!status?.show) {
    return null;
  }

  const hasStock = Boolean(status.stock);
  return (
    <Bento gold className="col-span-2 lg:col-span-4 mb-4 fade-up" testId="owner-onboarding-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="eyebrow mb-1">Setup Rider Pertama</p>
          <h2 className="font-heading text-xl font-bold">Siapkan {status.rider.name} untuk berjualan</h2>
        </div>
        <button
          data-testid="onboarding-stock-button"
          onClick={() => navigate("/rider-stock")}
          className="btn-primary h-11 px-4 text-xs"
        >
          {hasStock ? "Lihat Stock Awal" : "Buat Stock Awal"}
        </button>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <Step
          done={hasStock}
          icon={ClipboardList}
          title="1. Tetapkan stock awal"
          detail={hasStock ? `${status.stock.total} cup sudah dicatat.` : "Pilih Rider, isi stok dari pusat, lalu foto bukti."}
          testId="onboarding-step-stock"
        />
        <Step
          done={status.verified}
          icon={PackageCheck}
          title="2. Rider memverifikasi"
          detail={status.verified ? "Stock sudah diterima Rider." : "Minta Rider login dan verifikasi stock dengan foto."}
          testId="onboarding-step-verify"
        />
        <Step
          done={false}
          icon={Store}
          title="3. Mulai POS"
          detail="Setelah verifikasi, Rider dapat menerima pesanan di POS."
          testId="onboarding-step-pos"
        />
      </div>
    </Bento>
  );
}