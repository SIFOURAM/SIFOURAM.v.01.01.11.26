import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts";
import { Trophy, Calendar, MapPin, Wallet, FileDown, Printer } from "lucide-react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { api, errMsg } from "../lib/api";
import { fmtRp, fmtDate, initials, rangeFor, today } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Bento, Stat, DateFilter, Select, Empty, Field, ReceiptModal, RLine } from "../components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";

const COLORS = ["#FF6B00", "#F97316", "#EA580C", "#FB923C", "#C2410C", "#FDBA74", "#FF7A1A", "#E85D04", "#9A3412"];
const tip = { contentStyle: { borderRadius: 12, border: "1px solid #333", background: "#111", color: "#fff", fontSize: 12 } };
const RANK_ASSETS = {
  Herald: "/assets/rank-herald.png",
  Warriors: "/assets/rank-warriors.png",
  Masters: "/assets/rank-masters.png",
  Divine: "/assets/rank-divine.png",
  Immortal: "/assets/rank-immortal.png",
};

function RankCard({ data, onOpen }) {
  const rank = data.rank || {};
  return (
    <button data-testid="rider-rank-card" onClick={onOpen} className="col-span-2 lg:col-span-1 text-left">
      <Bento gold className="fade-up h-full overflow-hidden">
        <img src={RANK_ASSETS[rank.name]} alt={`Rank ${rank.name}`} className="w-full aspect-[16/7] object-cover rounded-lg" />
        <div className="mt-3 flex justify-between gap-3"><div><p className="eyebrow">Rank Mingguan</p><p className="font-heading font-bold text-xl">{rank.name}</p></div><div className="text-right"><p className="eyebrow">Estimasi Komisi Utama Anda</p><p className="num font-bold text-primary">{fmtRp(data.main_estimated_commission)}</p></div></div>
        <div className="mt-3 h-2 bg-muted overflow-hidden rounded-full"><div className="h-full bg-primary rounded-full" style={{ width: `${data.progress}%` }} /></div>
        <p className="text-xs text-muted-foreground mt-2">{rank.next ? `${fmtRp(data.remaining)} menuju ${rank.next.name}` : "Rank tertinggi tercapai"}</p>
      </Bento>
    </button>
  );
}

function RankDialog({ data, onClose }) {
  const rank = data.rank || {};
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent data-testid="rank-detail-dialog" className="max-w-md">
        <DialogHeader><DialogTitle>Rank {rank.name}</DialogTitle></DialogHeader>
        <img src={RANK_ASSETS[rank.name]} alt="Kartu rank rider" className="w-full rounded-lg" />
        <div className="grid grid-cols-2 gap-3 text-sm"><div className="bg-muted p-3 rounded-lg"><p className="eyebrow">Total penjualan</p><p className="num font-bold">{fmtRp(data.gross)}</p></div><div className="bg-muted p-3 rounded-lg"><p className="eyebrow">Hari hadir</p><p className="num font-bold">{data.attendance_days}</p></div><div className="bg-muted p-3 rounded-lg"><p className="eyebrow">Benefit hadir</p><p className="num font-bold">{fmtRp(rank.attendance_benefit)} / hari</p></div><div className="bg-primary/10 p-3 rounded-lg"><p className="eyebrow">Bonus penjualan</p><p className="num font-bold">{Math.round((rank.commission_pct || 0) * 100)}%</p></div></div>
        <p className="text-sm">Total benefit hadir: <b>{fmtRp(data.attendance_total)}</b> · Komisi estimasi: <b>{fmtRp(data.commission)}</b></p>
        <p className="text-xs text-muted-foreground">{rank.next ? `Target berikutnya ${rank.next.name}: ${fmtRp(rank.next.minimum)}.` : "Immortal adalah rank tertinggi."}</p>
      </DialogContent>
    </Dialog>
  );
}

export function TierProgress({ s, count = 1 }) {
  const { t } = useT();
  const nt = s.next_tier;
  const isTopRank = !nt && s.tier !== "Team" && s.tier !== "None";
  const progress = nt
    ? Math.min(100, (s.gross / (nt.threshold * count)) * 100)
    : isTopRank
      ? 100
      : 0;

  return (
    <div data-testid="tier-progress">
      <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
        <span className="flex items-center gap-2 text-sm font-semibold">
          <Trophy className="w-4 h-4 text-primary" />
          {s.tier === "None" ? "—" : s.tier}
          <span className="text-xs text-muted-foreground">
            ({Math.round(s.incentive_pct * 100)}%)
          </span>
        </span>
        {nt && (
          <span className="text-xs text-muted-foreground">
            {t("nextTier")}: <b className="text-foreground">{nt.name}</b> ·
            {fmtRp(nt.threshold * count)}
          </span>
        )}
      </div>
      <div className="h-3 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-primary to-[#F97316]"
          style={{ width: `${progress}%` }}
        />
      </div>
      {nt && (
        <p className="text-xs text-muted-foreground mt-2">
          {fmtRp(Math.max(0, nt.threshold * count - s.gross))} → {nt.name}
          {nt.min_days ? ` · min ${nt.min_days} ${t("attendance").toLowerCase()}` : ""}
        </p>
      )}
    </div>
  );
}

function WithdrawDialog({ type, s, range, onClose, onDone }) {
  const { t } = useT();
  const { user } = useAuth();
  const banks = s.banks || [];
  const primaryIdx = Math.max(0, banks.findIndex((b) => b.primary));
  const [f, setF] = useState({ method: banks.length ? "bank" : "cash", amount: "", date: today(), note: "", bank_idx: primaryIdx });
  const [hist, setHist] = useState([]);
  const [done, setDone] = useState(null);
  const [admins, setAdmins] = useState([]);
  const avail = type === "allowance" ? s.allowance_available : s.incentive_available;
  const load = () => api.get("/withdrawals", { params: { ...range, rider_id: s.rider_id } }).then((r) => setHist(r.data.filter((w) => w.type === type)));
  useEffect(() => { load(); api.get("/users", { params: { role: "owner" } }).then((r) => setAdmins(r.data.filter((u) => u.role === "owner"))).catch(() => {}); }, []); // eslint-disable-line
  const submit = async () => {
    const bk = f.method === "bank" ? banks[f.bank_idx] || {} : {};
    try { const { data } = await api.post("/withdrawals", { rider_id: s.rider_id, type, method: f.method, date: f.date, note: f.note, amount: Number(f.amount), bank_name: bk.bank_name, bank_account: bk.bank_account, bank_holder: bk.bank_holder }, { params: range }); toast.success(t("withdraw") + " ✓"); setF({ ...f, amount: "" }); load(); onDone(); setDone(data); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const label = type === "allowance" ? "UANG HARIAN" : "INSENTIF";
  const waText = done && `*SI FOUR AM — PENARIKAN ${label}*\n----------------------------------\n👤 *Rider:* ${done.rider_name}\n📅 *Tanggal:* ${fmtDate(done.date)} ${done.time} WIB\n💵 *Jumlah:* ${fmtRp(done.amount)}\n🏦 *Metode:* ${done.method === "bank" ? `Transfer Bank${done.bank_name ? ` — ${done.bank_name} ${done.bank_account || ""} a.n. ${done.bank_holder || done.rider_name}` : ""}` : "Cash"}\n📆 *Periode:* ${done.period_start} → ${done.period_end}\n📝 ${done.note || "-"}\n----------------------------------\nMohon diproses ya, terima kasih! 🙏`;
  if (done) return (
    <ReceiptModal open onClose={() => { setDone(null); onClose(); }} title={`Penarikan ${label}`} waText={waText} waPhone={admins[0]?.whatsapp} filename={`WD_${done.rider_name}_${done.date}.png`} testId="withdraw-receipt">
      <RLine l="Rider" r={done.rider_name} /><RLine l={t("date")} r={`${fmtDate(done.date)} ${done.time}`} /><RLine l={t("method")} r={done.method === "bank" ? `Bank · ${done.bank_name || "-"}` : "Cash"} />{done.method === "bank" && <RLine l="No. Rek" r={`${done.bank_account || "-"} (${done.bank_holder || done.rider_name})`} />}<RLine l={t("period")} r={`${done.period_start} → ${done.period_end}`} />
      <div className="border-t border-dashed border-gray-300 my-2" /><RLine bold l="JUMLAH" r={fmtRp(done.amount)} /><p className="text-[10px] text-gray-500 text-center mt-2">Kirim ke Superadmin: {admins[0]?.name}</p>
    </ReceiptModal>);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="withdraw-dialog"><DialogHeader><DialogTitle>{t("withdraw")} · {type === "allowance" ? t("dailyAllowance") : t("incentive")}</DialogTitle></DialogHeader>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-xl bg-muted p-2"><p className="eyebrow">{t("total")}</p><p className="num font-bold">{fmtRp(type === "allowance" ? s.allowance : s.incentive)}</p></div>
          <div className="rounded-xl bg-muted p-2"><p className="eyebrow">{t("withdraw")}</p><p className="num font-bold">{fmtRp(type === "allowance" ? s.allowance_withdrawn : s.incentive_withdrawn)}</p></div>
          <div className="rounded-xl bg-primary/10 p-2"><p className="eyebrow">{t("available")}</p><p data-testid="withdraw-available" className="num font-bold text-primary">{fmtRp(avail)}</p></div>
        </div>
        <div className="grid grid-cols-2 gap-3 mt-2">
          <Field label={t("method")}><Select testId="withdraw-method" value={f.method} onChange={(v) => setF({ ...f, method: v })} options={[{ value: "cash", label: "Cash" }, { value: "bank", label: t("bank") }]} /></Field>
          <Field label={t("date")}><input type="date" className="field" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></Field>
          <Field label={`${t("amount")} (Rp)`}><input data-testid="withdraw-amount" type="number" className="field num" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></Field>
          <Field label={t("note")}><input className="field" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></Field>
        </div>
        {f.method === "bank" && (banks.length > 0
          ? <div className="mt-2"><Field label="Rekening tujuan"><Select testId="withdraw-bank" value={String(f.bank_idx)} onChange={(v) => setF({ ...f, bank_idx: Number(v) })} options={banks.map((b, i) => ({ value: String(i), label: `${b.bank_name} · ${b.bank_account}` }))} /></Field></div>
          : <p data-testid="withdraw-no-bank" className="text-xs text-amber-500 mt-2">Belum ada rekening bank. Tambahkan dulu di menu Profil.</p>)}
        <button data-testid="withdraw-submit" onClick={submit} disabled={!f.amount || Number(f.amount) > avail} className="btn-primary w-full">{t("withdraw")}</button>
        <p className="eyebrow mt-2">{t("withdrawals")}</p>
        <div className="max-h-40 overflow-y-auto text-xs">{hist.map((w) => <div key={w.id} className="flex justify-between py-1.5 border-b border-border/40"><span className="num">{w.date} {w.time} · {w.method.toUpperCase()}</span><b className="num">{fmtRp(w.amount)}</b></div>)}{!hist.length && <Empty text={t("noData")} />}</div>
      </DialogContent>
    </Dialog>
  );
}

export default function RiderDashboard() {
  const { t, lang } = useT();
  const { user } = useAuth();
  const [sp] = useSearchParams();
  const isRider = user.role === "rider";
  const [riders, setRiders] = useState([]);
  const [riderId, setRiderId] = useState(isRider ? user.id : sp.get("rider") || "all");
  const [range, setRange] = useState(() => rangeFor("today"));
  const [sum, setSum] = useState(null);
  const [sal, setSal] = useState(null);
  const [stockHist, setStockHist] = useState([]);
  const [sales, setSales] = useState([]);
  const [deps, setDeps] = useState([]);
  const [wd, setWd] = useState(null);
  const [rank, setRank] = useState(null);
  const [showRank, setShowRank] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const tableRef = useRef();
  const lastLoadKey = useRef("");

  useEffect(() => {
    if (!isRider) {
      api.get("/users", { params: { role: "rider" } })
        .then((response) => setRiders(response.data))
        .catch((error) => {
          setRiders([]);
          toast.error(errMsg(error));
        });
    }
  }, [isRider]);

  const load = useCallback(async (force = false) => {
    if (!range) return;
    const loadKey = `${range.start}:${range.end}:${riderId}`;
    if (!force && lastLoadKey.current === loadKey) return;

    lastLoadKey.current = loadKey;
    setLoading(true);
    setLoadError("");
    const p = { ...range, ...(riderId !== "all" ? { rider_id: riderId } : {}) };
    try {
      const responses = await Promise.all([
        api.get("/dashboard/summary", { params: p }),
        api.get("/salary", { params: p }),
        api.get("/rider-stock/history", { params: p }),
        api.get("/sales", { params: p }),
        api.get("/deposits", { params: p }),
        riderId !== "all" ? api.get("/rider-rank", { params: p }) : Promise.resolve(null),
      ]);
      setSum(responses[0].data);
      setSal(responses[1].data);
      setStockHist(responses[2].data);
      setSales(responses[3].data);
      setDeps(responses[4].data);
      setRank(responses[5]?.data || null);
    } catch (error) {
      setLoadError(errMsg(error));
      toast.error(`Dashboard Rider gagal dimuat: ${errMsg(error)}`);
    } finally {
      setLoading(false);
    }
  }, [range, riderId]);

  useEffect(() => {
    load();
  }, [load]);

  const rider = isRider ? user : riders.find((r) => r.id === riderId);
  const agg = sal && (riderId !== "all" ? sal.riders[0] : (() => {
    const n = sal.riders.length;
    const S = (k) => sal.riders.reduce((s, r) => s + (r[k] || 0), 0);
    const nearest = sal.riders.map((r) => r.next_tier).filter(Boolean).sort((a, b) => a.threshold - b.threshold)[0];
    return { gross: S("gross"), cups: S("cups"), attendance_days: S("attendance_days"), allowance: S("allowance"), allowance_available: S("allowance_available"), incentive: S("incentive"), incentive_available: S("incentive_available"), total_income: S("total_income"), tier: "Team", incentive_pct: 0, next_tier: nearest, count: n };
  })());
  const single = riderId !== "all" && agg;

  const exportPdf = () => {
    const doc = new jsPDF(); doc.setFontSize(14); doc.text(`SI FOUR AM — ${rider?.name || t("allRiders")} · ${range.start} → ${range.end}`, 14, 16);
    autoTable(doc, { startY: 22, head: [[t("date"), t("rider"), "Cups", "Cash", "QRIS", "Net"]], body: deps.map((d) => [d.date, d.rider_name, d.total_cups, d.total_cash.toLocaleString("id-ID"), d.total_qris.toLocaleString("id-ID"), d.net_cash.toLocaleString("id-ID")]), styles: { fontSize: 8 }, headStyles: { fillColor: [255, 107, 0] } });
    doc.save("DataDeposit_SIFOURAM.pdf");
  };
  const printTable = () => { const w = window.open("", "_blank"); w.document.write(`<html><head><title>Print Data</title></head><body style="background:#111;color:#fff;font-family:Arial"><style>table{border-collapse:collapse;width:100%}td,th{border:1px solid #444;padding:6px;font-size:12px}</style>${tableRef.current.innerHTML}</body></html>`); w.document.close(); w.print(); };

  return (
    <div data-testid="rider-dashboard">
      <PageHeader eyebrow={isRider ? (lang === "id" ? "Performa saya" : "My performance") : "Riders"} title={t("riderDash")}>
        {!isRider && <Select testId="rider-dash-select" value={riderId} onChange={setRiderId} className="w-44" options={[{ value: "all", label: t("allRiders") }, ...riders.map((r) => ({ value: r.id, label: r.name }))]} />}
      </PageHeader>
      {loading && (
        <div data-testid="rider-dashboard-loading" className="py-14 text-center text-sm text-muted-foreground">
          Memuat dashboard rider…
        </div>
      )}
      {loadError && !loading && (
        <div data-testid="rider-dashboard-error" role="alert" className="py-14 text-center">
          <p className="text-sm text-destructive">Dashboard Rider gagal dimuat: {loadError}</p>
          <button
            data-testid="rider-dashboard-retry-button"
            onClick={() => load(true)}
            className="btn-primary mt-4"
          >
            Coba lagi
          </button>
        </div>
      )}
      {!loading && !loadError && sum && agg && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          <Bento gold className="col-span-2 lg:col-span-1 fade-up flex flex-col items-center text-center" testId="rider-profile-card">
            <div className="w-20 h-20 rounded-full border-2 border-black overflow-hidden bg-primary text-black font-bold text-2xl flex items-center justify-center mb-3">{rider?.photo ? <img src={rider.photo} alt="" className="w-full h-full object-cover" /> : rider ? initials(rider.name) : "ALL"}</div>
            <p className="font-heading font-bold text-lg">{rider?.name || t("allRiders")}</p>
            {rider && <><p className="text-xs text-muted-foreground flex items-center gap-1 mt-1"><Calendar className="w-3 h-3" />{t("joined")} {rider.joined_at ? fmtDate(rider.joined_at) : "-"}</p>
              <p className="text-xs text-muted-foreground flex items-center gap-1"><MapPin className="w-3 h-3" />{rider.placement || "-"}</p></>}
            <div className="mt-4 w-full rounded-xl bg-muted p-3"><p className="eyebrow">{t("totalIncome")}</p><p data-testid="rider-total-income" className="num font-bold text-primary">{fmtRp(agg.total_income)}</p></div>
          </Bento>
          <Bento className="col-span-2 lg:col-span-3 fade-up" testId="rider-period-filter"><p className="eyebrow mb-3">Filter periode</p><DateFilter onChange={setRange} riderPeriods={isRider} /></Bento>
          <Bento className="fade-up" testId="rider-stat-allowance"><div className="flex justify-between items-start"><p className="eyebrow">{t("dailyAllowance")}</p><Wallet className="w-4 h-4 text-primary" /></div>
            <p className="mt-3 text-2xl font-bold num font-heading">{fmtRp(agg.allowance)}</p><p className="text-xs text-muted-foreground">{t("available")}: <b className="num">{fmtRp(agg.allowance_available)}</b></p>
            {single && <button data-testid="withdraw-allowance-button" onClick={() => setWd("allowance")} className="btn-primary h-9 mt-3 w-full text-xs">{t("withdraw")}</button>}</Bento>
          <Bento className={`fade-up ${single ? "cursor-pointer hover:border-primary/50" : ""}`} testId="rider-stat-incentive">
            <button data-testid="incentive-card-button" disabled={!single} onClick={() => setWd("incentive")} className="w-full text-left">
              <p className="eyebrow">{t("incentive")} · {agg.tier}</p><p className="mt-3 text-2xl font-bold num font-heading">{fmtRp(agg.incentive)}</p><p className="text-xs text-muted-foreground">{t("available")}: <b className="num">{fmtRp(agg.incentive_available)}</b>{single && ` · ${t("withdraw")} →`}</p></button></Bento>
          <Stat label={t("totalCups")} value={sum.cups} sub={`${agg.attendance_days} ${t("attendance").toLowerCase()} · ${fmtRp(agg.gross)}`} testId="rider-stat-cups" />

          {rank && <RankCard data={rank} onOpen={() => setShowRank(true)} />}

          <Bento className="col-span-2 lg:col-span-4 fade-up" testId="tier-card">
            <p className="eyebrow mb-4">
              {t("nextTier")}{riderId === "all" ? ` (× ${agg.count} riders)` : ""}
            </p>
            {riderId === "all" && !agg.count ? (
              <div data-testid="rider-tier-empty">
                <Empty text="Belum ada rider aktif untuk ditampilkan." />
              </div>
            ) : (
              <TierProgress s={agg} count={riderId === "all" ? agg.count : 1} />
            )}
          </Bento>

          <Bento className="col-span-2 fade-up" testId="chart-daily">
            <p className="eyebrow mb-4">{t("dailySales")} (Cash + QRIS)</p>
            {sum.by_date.length ? <ResponsiveContainer width="100%" height={220}><LineChart data={sum.by_date.map((d) => ({ d: d.date.slice(5), v: d.cash + d.qris }))}><CartesianGrid strokeDasharray="3 3" stroke="#3333" /><XAxis dataKey="d" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis hide /><Tooltip {...tip} formatter={(v) => fmtRp(v)} /><Line type="monotone" dataKey="v" stroke="#F97316" strokeWidth={2.5} dot={{ fill: "#FF6B00", r: 3 }} /></LineChart></ResponsiveContainer> : <Empty text={t("noData")} />}
          </Bento>
          <Bento className="col-span-2 fade-up" testId="chart-best-selling">
            <p className="eyebrow mb-4">{t("bestSelling")}</p>
            {sum.by_menu.length ? <div className="flex items-center gap-4"><ResponsiveContainer width="50%" height={200}><PieChart><Pie data={sum.by_menu} dataKey="qty" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={3}>{sum.by_menu.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip {...tip} /></PieChart></ResponsiveContainer>
              <ul className="text-xs space-y-1 flex-1">{sum.by_menu.slice(0, 6).map((m, i) => <li key={m.name} className="flex justify-between"><span className="flex items-center gap-2 truncate"><span className="w-2 h-2 rounded-full shrink-0" style={{ background: COLORS[i] }} />{m.name}</span><b className="num">{m.qty}</b></li>)}</ul></div> : <Empty text={t("noData")} />}
          </Bento>

          <Bento className="col-span-2 fade-up" testId="stock-photo-history">
            <p className="eyebrow mb-4">{t("photoEvidence")}</p>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">{stockHist.filter((h) => h.photo).slice(0, 8).map((h) => <div key={h.id} className="relative rounded-xl overflow-hidden aspect-square"><img src={h.photo} alt="" className="w-full h-full object-cover" /><span className="absolute bottom-1 left-1 text-[9px] bg-black/60 text-white px-1.5 rounded">{h.date} · {h.total}</span></div>)}</div>
            {!stockHist.filter((h) => h.photo).length && <Empty text={t("noData")} />}
          </Bento>
          <Bento className="col-span-2 fade-up" testId="rider-sales-history">
            <div className="flex items-center justify-between mb-3"><p className="eyebrow">{t("history")} (deposit)</p><div className="flex gap-1"><button data-testid="export-pdf-button" onClick={exportPdf} className="btn-ghost h-8 px-3 text-xs"><FileDown className="w-3 h-3" />PDF</button><button data-testid="print-button" onClick={printTable} className="btn-ghost h-8 px-3 text-xs"><Printer className="w-3 h-3" />{t("print")}</button></div></div>
            <div ref={tableRef} className="max-h-72 overflow-y-auto"><table className="table-x" id="tabelUtamaID"><thead><tr><th>{t("date")}</th><th>{t("rider")}</th><th>Cups</th><th>Cash</th><th>QRIS</th></tr></thead>
              <tbody>{deps.map((d) => <tr key={d.id}><td className="num text-xs">{d.date}</td><td className="text-xs">{d.rider_name}</td><td className="num">{d.total_cups}</td><td className="num text-xs">{fmtRp(d.total_cash)}</td><td className="num text-xs">{fmtRp(d.total_qris)}</td></tr>)}
                {sales.slice(0, 20).map((s) => <tr key={s.id} className="text-muted-foreground"><td className="num text-xs">{s.date} {s.time}</td><td className="text-xs">POS {s.receipt_no}</td><td className="num">{s.cups}</td><td className="num text-xs">{s.payment_method === "cash" ? fmtRp(s.total) : "-"}</td><td className="num text-xs">{s.payment_method === "qris" ? fmtRp(s.total) : "-"}</td></tr>)}</tbody></table>
              {!deps.length && !sales.length && <Empty text={t("noData")} />}</div>
          </Bento>
        </div>
      )}
      {wd && single && <WithdrawDialog type={wd} s={agg} range={range} onClose={() => setWd(null)} onDone={() => load(true)} />}
      {showRank && rank && <RankDialog data={rank} onClose={() => setShowRank(false)} />}
    </div>
  );
}
