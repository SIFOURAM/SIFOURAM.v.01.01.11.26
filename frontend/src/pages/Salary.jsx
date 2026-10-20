import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Camera } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { fmtRp, initials, compressImage } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { PageHeader, Bento, DateFilter, Empty } from "../components/common";
import { TierProgress } from "./RiderDashboard";

export default function Salary() {
  const { t } = useT();
  const { user } = useAuth();
  const nav = useNavigate();
  const [range, setRange] = useState(null);
  const [d, setD] = useState(null);
  const [wds, setWds] = useState([]);
  const loadWds = () => range && api.get("/withdrawals", { params: range }).then((r) => setWds(r.data)).catch(() => {});
  useEffect(() => { if (range) { api.get("/salary", { params: range }).then((r) => setD(r.data)); loadWds(); } }, [range]); // eslint-disable-line
  const accept = async (id) => { try { await api.post(`/withdrawals/${id}/accept`); toast.success("Ditandai diterima ✓"); loadWds(); } catch { toast.error("Gagal menandai"); } };
  const changePhoto = async (rid, file) => {
    try { const photo = await compressImage(file); const { data } = await api.put(`/users/${rid}/photo`, { photo });
      setD((prev) => ({ ...prev, riders: prev.riders.map((x) => (x.rider_id === rid ? { ...x, photo: data.photo } : x)) })); toast.success("Foto rider diperbarui ✓"); }
    catch { toast.error("Gagal mengunggah foto"); }
  };
  return (
    <div data-testid="salary-page">
      <PageHeader eyebrow="Trader income" title={t("salary")}><DateFilter onChange={setRange} /></PageHeader>
      {d && (<>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {d.tiers.map((tr, i) => <Bento key={tr.name} gold={i === 3} className="fade-up" testId={`tier-${tr.name.toLowerCase()}`}><p className="eyebrow">{tr.name}</p><p className="font-heading font-bold text-xl mt-1">{Math.round(tr.pct * 100)}%</p><p className="text-xs text-muted-foreground num">≥ {fmtRp(tr.threshold)}{tr.min_days ? ` · ${tr.min_days}+ days` : ""}</p></Bento>)}
        </div>
        <p className="text-xs text-muted-foreground mb-4">{t("dailyAllowance")} Rp 20.000 / {t("attendance").toLowerCase()}. {t("period")}: 16 → 15.</p>
        <div className="grid md:grid-cols-2 gap-4">
          {d.riders.map((r) => (
            <Bento key={r.rider_id} className="fade-up" testId={`salary-card-${r.rider_id}`}>
              <div className="flex items-center gap-3 mb-4">
                <div className="relative w-11 h-11 shrink-0">
                  <div className="w-11 h-11 rounded-full bg-primary/15 text-primary font-bold flex items-center justify-center overflow-hidden">{r.photo ? <img src={r.photo} alt="" className="w-full h-full object-cover" /> : initials(r.rider_name)}</div>
                  {user.role === "owner" && <label className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-primary text-white flex items-center justify-center cursor-pointer shadow"><Camera className="w-3 h-3" /><input type="file" accept="image/*" className="hidden" data-testid={`salary-photo-${r.rider_id}`} onChange={(e) => e.target.files[0] && changePhoto(r.rider_id, e.target.files[0])} /></label>}
                </div>
                <div className="flex-1"><button data-testid={`salary-rider-link-${r.rider_id}`} onClick={() => nav(`/rider-dashboard?rider=${r.rider_id}`)} className="font-heading font-bold text-primary hover:underline text-left">{r.rider_name} →</button><p className="text-xs text-muted-foreground">{r.cups} cups · {r.attendance_days} {t("attendance").toLowerCase()}</p></div>
                <div className="text-right"><p className="eyebrow">{t("totalIncome")}</p><p className="num font-bold text-primary">{fmtRp(r.total_income)}</p></div></div>
              <div className="grid grid-cols-3 gap-2 text-center mb-4">
                <div className="rounded-xl bg-muted p-2"><p className="eyebrow">Gross</p><p className="num text-xs font-bold">{fmtRp(r.gross)}</p></div>
                <div className="rounded-xl bg-muted p-2"><p className="eyebrow">{t("dailyAllowance")}</p><p className="num text-xs font-bold">{fmtRp(r.allowance)}</p><p className="text-[10px] text-muted-foreground">{r.attendance_days} {t("attendance").toLowerCase()}</p></div>
                <div className="rounded-xl bg-muted p-2"><p className="eyebrow">Incentive</p><p className="num text-xs font-bold">{fmtRp(r.incentive)}</p></div>
              </div>
              <TierProgress s={r} />
              {(() => { const rw = wds.filter((w) => w.rider_id === r.rider_id); return rw.length > 0 ? (
                <div className="mt-4 border-t border-border/40 pt-3 space-y-1.5" data-testid={`wd-list-${r.rider_id}`}>
                  <p className="eyebrow">Pencairan Gaji / Insentif</p>
                  {rw.map((w) => (
                    <div key={w.id} className="flex items-center justify-between gap-2 text-xs">
                      <span className="truncate flex-1">{w.date} · {w.type === "allowance" ? "Uang Harian" : "Insentif"} · {w.method.toUpperCase()}</span>
                      <b className="num">{fmtRp(w.amount)}</b>
                      {w.status === "diterima"
                        ? <span data-testid={`wd-status-${w.id}`} className="shrink-0 text-[10px] font-bold text-emerald-500 bg-emerald-500/10 rounded-full px-2 py-0.5">Diterima ✓</span>
                        : user.role === "owner"
                          ? <button data-testid={`wd-accept-${w.id}`} onClick={() => accept(w.id)} className="shrink-0 text-[10px] font-bold text-primary border border-primary/50 rounded-full px-2 py-0.5 hover:bg-primary hover:text-white transition-colors">Diterima</button>
                          : <span data-testid={`wd-status-${w.id}`} className="shrink-0 text-[10px] font-semibold text-amber-500 bg-amber-500/10 rounded-full px-2 py-0.5">Pending</span>}
                    </div>))}
                </div>) : null; })()}
            </Bento>))}
          {!d.riders.length && <Empty text={t("noData")} />}
        </div>
      </>)}
    </div>
  );
}
