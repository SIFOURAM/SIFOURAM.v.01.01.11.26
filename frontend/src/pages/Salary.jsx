import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Camera, ChevronDown, Pencil } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { fmtRp, initials, compressImage } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { PageHeader, Bento, DateFilter, Empty } from "../components/common";
import { RANK_ASSETS, TierProgress } from "./RiderDashboard";

export default function Salary() {
  const { t } = useT();
  const { user } = useAuth();
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const targetRider = sp.get("rider");
  const [range, setRange] = useState(null);
  const [d, setD] = useState(null);
  const [wds, setWds] = useState([]);
  const [expandedTier, setExpandedTier] = useState(null);
  const [rankSettings, setRankSettings] = useState([]);
  const [editingRank, setEditingRank] = useState(null);
  const [savingRank, setSavingRank] = useState(false);
  const tierDetailRef = useRef(null);
  const compactRp = (value) => value >= 1000000 ? `Rp${(value / 1000000).toLocaleString("id-ID", { maximumFractionDigits: 2 })}jt` : fmtRp(value);
  const formatTierRange = (tier, compact = false) => {
    const start = compact ? compactRp(tier.threshold) : fmtRp(tier.threshold);
    const end = tier.maximum ? (compact ? compactRp(tier.maximum - 1) : fmtRp(tier.maximum - 1)) : "+";
    return `${start}${tier.maximum ? ` – ${end}` : end}`;
  };
  const loadWds = () => range && api.get("/withdrawals", { params: range }).then((r) => setWds(r.data)).catch(() => {});
  useEffect(() => {
    if (!range) return undefined;
    const loadSalary = () => {
      if (document.visibilityState === "hidden") return;
      api.get("/salary", { params: { ...range, ...(targetRider ? { rider_id: targetRider } : {}) } }).then((r) => setD(r.data)).catch(() => {});
      loadWds();
    };
    loadSalary();
    const polling = window.setInterval(loadSalary, 30000);
    document.addEventListener("visibilitychange", loadSalary);
    return () => {
      window.clearInterval(polling);
      document.removeEventListener("visibilitychange", loadSalary);
    };
  }, [range, targetRider]); // eslint-disable-line
  const accept = async (id) => { try { await api.post(`/withdrawals/${id}/accept`); toast.success("Ditandai diterima ✓"); loadWds(); } catch { toast.error("Gagal menandai"); } };
  const changePhoto = async (rid, file) => {
    try { const photo = await compressImage(file); const { data } = await api.put(`/users/${rid}/photo`, { photo });
      setD((prev) => ({ ...prev, riders: prev.riders.map((x) => (x.rider_id === rid ? { ...x, photo: data.photo } : x)) })); toast.success("Foto rider diperbarui ✓"); }
    catch { toast.error("Gagal mengunggah foto"); }
  };
  const openTier = (tierName) => {
    const nextTier = expandedTier === tierName ? null : tierName;
    setExpandedTier(nextTier);
    if (nextTier) window.setTimeout(() => tierDetailRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 0);
  };
  const openRankEditor = async (tierName) => {
    try {
      const { data } = await api.get("/rider-ranks");
      setRankSettings(data);
      setEditingRank(tierName);
    } catch { toast.error("Target Rank belum dapat dimuat."); }
  };
  const saveRank = async () => {
    setSavingRank(true);
    try {
      await api.put("/rider-ranks", rankSettings);
      toast.success("Target Rank berhasil disimpan.");
      setEditingRank(null);
    } catch { toast.error("Target Rank gagal disimpan."); } finally { setSavingRank(false); }
  };
  return (
    <div data-testid="salary-page">
      <PageHeader eyebrow="Target mingguan" title={t("salary")}><DateFilter onChange={setRange} riderPeriods initialPreset="week" /></PageHeader>
      {d && (<>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {d.tiers.map((tr) => <Bento key={tr.name} gold className="fade-up overflow-hidden p-0" testId={`tier-${tr.name.toLowerCase()}`}><div className="relative"><button data-testid={`tier-open-${tr.name.toLowerCase()}`} onClick={() => openTier(tr.name)} className="w-full text-left"><img src={RANK_ASSETS[tr.name]} alt={`Kartu ${tr.name}`} className="w-full aspect-[16/8] object-cover" /><div className="p-4"><p className="eyebrow">{tr.name}</p><p title={`${formatTierRange(tr)} / minggu`} className="font-heading font-bold text-xs leading-tight sm:text-sm mt-1">{formatTierRange(tr, true)} / minggu</p><p className="text-[10px] leading-tight text-muted-foreground">Hadir {compactRp(tr.attendance_benefit)}/hari · bonus {Math.round(tr.pct * 100)}%</p></div></button>{user.role === "owner" && <button data-testid={`salary-edit-rank-${tr.name.toLowerCase()}`} onClick={() => openRankEditor(tr.name)} className="absolute left-2 top-2 flex h-8 w-8 items-center justify-center rounded-md bg-primary text-white shadow" aria-label={`Edit ${tr.name}`}><Pencil className="h-3.5 w-3.5" /></button>}</div></Bento>)}
        </div>
        {editingRank && (() => { const index = rankSettings.findIndex((rank) => rank.name === editingRank); const rank = rankSettings[index]; return rank && <Bento gold data-testid="rank-target-editor" className="mb-4"><p className="font-heading font-bold">Edit Target Rank {rank.name}</p><div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4"><label className="text-xs">Minimum<input data-testid="rank-minimum-input" type="number" className="field mt-1" value={rank.minimum} onChange={(event) => setRankSettings((all) => all.map((item, itemIndex) => itemIndex === index ? { ...item, minimum: Number(event.target.value) } : item))} /></label><label className="text-xs">Maksimum<input data-testid="rank-maximum-input" type="number" className="field mt-1" value={rank.maximum || ""} onChange={(event) => setRankSettings((all) => all.map((item, itemIndex) => itemIndex === index ? { ...item, maximum: event.target.value ? Number(event.target.value) : null } : item))} /></label><label className="text-xs">Benefit hadir<input data-testid="rank-attendance-input" type="number" className="field mt-1" value={rank.attendance_benefit} onChange={(event) => setRankSettings((all) => all.map((item, itemIndex) => itemIndex === index ? { ...item, attendance_benefit: Number(event.target.value) } : item))} /></label><label className="text-xs">Komisi %<input data-testid="rank-commission-input" type="number" step="0.1" className="field mt-1" value={rank.commission_pct * 100} onChange={(event) => setRankSettings((all) => all.map((item, itemIndex) => itemIndex === index ? { ...item, commission_pct: Number(event.target.value) / 100 } : item))} /></label></div><div className="mt-4 flex gap-2"><button data-testid="rank-save-button" onClick={saveRank} disabled={savingRank} className="btn-primary">Simpan Target</button><button onClick={() => setEditingRank(null)} className="btn-ghost">Batal</button></div></Bento>; })()}
        {expandedTier && (() => { const tier = d.tiers.find((item) => item.name === expandedTier); return <div ref={tierDetailRef}><Bento gold className="mb-4 fade-up" testId="tier-detail-panel"><div className="flex items-center justify-between gap-3"><div><p className="eyebrow">Detail Target {tier.name}</p><p className="font-heading font-bold text-lg">{formatTierRange(tier)} / minggu</p></div><ChevronDown className="w-4 h-4 text-primary" /></div><div className="grid grid-cols-2 gap-3 mt-3 text-xs"><div><p className="eyebrow">Kehadiran</p><p className="num font-bold">{fmtRp(tier.attendance_benefit)} / hari</p></div><div><p className="eyebrow">Bonus Penjualan</p><p className="num font-bold">{Math.round(tier.pct * 100)}% dari total penjualan</p></div></div></Bento></div>; })()}
        <p className="text-xs text-muted-foreground mb-4">Benefit kehadiran dan bonus penjualan mengikuti rank yang tercapai pada periode pilihan.</p>
        <Bento gold className="mb-4" testId="rider-live-sales-detail"><p className="eyebrow">Data Rider dengan Target yang Sedang Tercapai</p><p className="text-[10px] text-muted-foreground">Penjualan real time dan target rank aktif diperbarui otomatis setiap 30 detik.</p><div className="mt-3 space-y-2">{d.riders.map((r) => <div key={r.rider_id} data-testid={`rider-live-sales-${r.rider_id}`} className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 border-b border-border/50 pb-2 last:border-0 last:pb-0"><div className="min-w-0"><p className="truncate text-xs font-semibold">{r.rider_name}</p><p className="text-[10px] text-primary">Target tercapai: {r.tier}{r.next_tier ? ` · Target berikutnya ${r.next_tier.name}` : ""}</p></div><div className="text-right"><p className="num text-xs font-bold">{fmtRp(r.gross)}</p><p className="num text-[10px] text-muted-foreground">{r.next_tier ? `${r.next_tier.progress}% target` : "100% target"}</p></div></div>)}{!d.riders.length && <Empty text={t("noData")} />}</div></Bento>
        <div className="grid md:grid-cols-2 gap-4">
          {d.riders.map((r) => (
            <Bento key={r.rider_id} gold={r.rider_id === targetRider} className="fade-up" testId={`salary-card-${r.rider_id}`}>
              <div className="flex items-center gap-3 mb-4">
                <div className="relative w-11 h-11 shrink-0">
                  <div className="w-11 h-11 rounded-full bg-primary/15 text-black font-bold flex items-center justify-center overflow-hidden">{r.photo ? <img src={r.photo} alt="" className="w-full h-full object-cover" /> : initials(r.rider_name)}</div>
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
