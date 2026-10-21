import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { today, shareReceipt, fmtDate } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Bento, Field, Select, QtySelect, PhotoCapture, Empty, DateFilter } from "../components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";

function RiderPickup({ user, view }) {
  const [stock, setStock] = useState(null);
  const [detail, setDetail] = useState(false);
  const [busy, setBusy] = useState(false);
  const [verificationPhoto, setVerificationPhoto] = useState(null);
  const load = useCallback(() => {
    return api.get("/rider-stock", { params: { rider_id: user.id, date: today() } })
      .then((response) => setStock(response.data))
      .catch(() => setStock(null));
  }, [user.id]);
  useEffect(() => { load(); }, [load]);
  const verify = async () => {
    if (!verificationPhoto) return toast.error("Ambil foto bukti penerimaan stock terlebih dahulu.");
    setBusy(true);
    try {
      await api.post(`/rider-stock/${stock.id}/verify`, { photo: verificationPhoto });
      toast.success("Stock awal diverifikasi · POS siap digunakan");
      setVerificationPhoto(null);
      setDetail(false);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  if (view === "remaining") return <RiderRemaining user={user} />;
  return <div data-testid="rider-pickup-page"><PageHeader /><Bento gold><p className="eyebrow mb-2">Stock Awal Hari Ini</p>{stock ? <><p className="font-heading text-xl font-bold">Dari {stock.pic_name}</p><p className="text-sm text-muted-foreground">{fmtDate(stock.date)} · {stock.total} cup</p><button data-testid="pickup-detail-button" onClick={() => setDetail(true)} className="btn-primary mt-4">Lihat & Verifikasi</button></> : <Empty text="Belum ada stock awal untuk hari ini" />}</Bento>{detail && stock && <Dialog open onOpenChange={(open) => !open && setDetail(false)}><DialogContent data-testid="pickup-detail-dialog" className="max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>Verifikasi Stock Awal</DialogTitle></DialogHeader><p className="text-sm">Pemberi stock: <b>{stock.pic_name}</b></p><div className="space-y-2">{Object.entries(stock.detail || stock.items).map(([name, qty]) => <div key={name} className="flex justify-between text-sm"><span>{name}</span><b>{qty}</b></div>)}</div>{stock.photo && <img src={stock.photo} alt="Bukti stock awal" className="w-full rounded-lg max-h-52 object-cover" />}{stock.verified_at ? <p data-testid="pickup-verified-status" className="text-emerald-600 font-bold text-sm">✓ Sudah diverifikasi</p> : <><p className="eyebrow">Foto bukti penerimaan *</p><PhotoCapture value={verificationPhoto} onChange={setVerificationPhoto} testId="pickup-verification-photo" label="Foto stock yang diterima" /><button data-testid="pickup-verify-button" disabled={busy || !verificationPhoto} onClick={verify} className="btn-primary w-full">Verifikasi & Isi Stock POS</button></>}</DialogContent></Dialog>}</div>;
}

function RiderRemaining({ user }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/rider-stock/remaining", { params: { date: today() } }).then((response) => setRows(response.data)).catch(() => setRows([])); }, []);
  const row = rows.find((item) => item.rider_id === user.id);
  return <div data-testid="rider-stock-remaining-page"><PageHeader /><Bento gold>{row ? <><p className="font-heading font-bold">Sisa Stock Hari Ini</p><p className="text-xs text-muted-foreground mb-3">Terjual {row.sold_total} · Sisa {row.remaining_total}</p>{row.items.map((item) => <div key={item.menu_id} className="flex justify-between text-sm py-1 border-b border-border/40"><span>{item.name}</span><b>{item.remaining}</b></div>)}</> : <Empty text="Belum ada stock Rider pada hari ini." />}</Bento></div>;
}

export default function RiderStock() {
  const { t, lang } = useT();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [fc, setFc] = useState(null);
  const [riders, setRiders] = useState([]);
  const [menus, setMenus] = useState([]);
  const [riderId, setRiderId] = useState("");
  const [date, setDate] = useState(today());
  const [range, setRange] = useState({ start: today(), end: today() });
  const [items, setItems] = useState({});
  const [photo, setPhoto] = useState(null);
  const [history, setHistory] = useState([]);
  const [remainingRows, setRemainingRows] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const view = searchParams.get("view") || "initial";

  useEffect(() => {
    if (user.role === "rider") return;
    api.get("/users", { params: { role: "rider" } })
      .then((response) => setRiders(response.data))
      .catch((error) => toast.error(errMsg(error)));
    api.get("/menus")
      .then((response) => setMenus(response.data))
      .catch((error) => toast.error(errMsg(error)));
  }, [user.role]);
  useEffect(() => {
    if (user.role === "rider") return;
    if (!riderId) return;
    api.get("/rider-stock", { params: { rider_id: riderId, date } }).then((r) => { setItems(r.data?.items || {}); setPhoto(r.data?.photo || null); });
    api.get("/rider-stock/history", { params: { rider_id: riderId, ...range } }).then((r) => setHistory(r.data));
  }, [riderId, date, range, user.role]);

  useEffect(() => {
    if (view !== "remaining") return;
    const params = { ...range, ...(riderId ? { rider_id: riderId } : {}) };
    api.get("/rider-stock/remaining", { params })
      .then((response) => setRemainingRows(response.data))
      .catch((error) => toast.error(errMsg(error)));
  }, [range, riderId, view]);

  if (user.role === "rider") return <RiderPickup user={user} view={view} />;

  if (view === "remaining") return <div data-testid="rider-stock-remaining-page"><PageHeader eyebrow="Stock" title="Sisa" /><Bento className="mb-5"><DateFilter onChange={setRange} riderPeriods initialPreset="today" /><Field label={t("selectRider")} className="mt-3"><Select testId="remaining-rider-select" value={riderId} onChange={setRiderId} placeholder="Semua Rider" options={riders.map((item) => ({ value: item.id, label: item.name }))} /></Field></Bento>{remainingRows.map((row) => <Bento key={row.stock_id} testId={`remaining-row-${row.stock_id}`} className="mb-3"><div className="flex justify-between gap-3"><div><p className="font-heading font-bold">{row.rider_name}</p><p className="text-xs text-muted-foreground">{fmtDate(row.date)} · Awal {row.initial_total} · Terjual {row.sold_total}</p></div><p className="num font-bold text-primary">Sisa {row.remaining_total}</p></div><div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">{row.items.map((item) => <div key={item.menu_id} className="bg-muted p-2 rounded-lg"><p className="truncate">{item.name}</p><p className="num">Awal {item.initial}</p><p className="num">Terjual {item.sold}</p><p className="num">Sisa {item.remaining}</p><p className="num text-primary">Selisih {item.initial - item.sold - item.remaining}</p></div>)}</div></Bento>)}{!remainingRows.length && <Empty text="Belum ada stock Rider pada periode ini." />}</div>;

  if (view === "rider" || view === "pickup") return <div data-testid="stock-rider-audit-page"><PageHeader eyebrow="Stock" title={view === "pickup" ? "Pengambilan" : "Stock Rider"} /><Bento className="mb-5"><div className="grid sm:grid-cols-2 gap-3"><Field label={t("selectRider")}><Select testId="stock-audit-rider-select" value={riderId} onChange={setRiderId} placeholder="Pilih Rider" options={riders.map((item) => ({ value: item.id, label: item.name }))} /></Field><div><p className="eyebrow mb-2">Filter periode</p><DateFilter onChange={setRange} riderPeriods initialPreset="today" /></div></div></Bento>{history.map((stock) => <Bento key={stock.id} className="mb-3" testId={`stock-audit-${stock.id}`}><button data-testid={`stock-audit-open-${stock.id}`} onClick={() => setSelectedStock(stock)} className="w-full text-left"><div className="flex gap-3 items-center"><img src={stock.photo} alt="Bukti stock awal" className="w-14 h-14 rounded-lg object-cover bg-muted" /><div className="flex-1"><p className="font-heading font-bold">{stock.rider_name}</p><p className="text-xs text-muted-foreground">{fmtDate(stock.date)} · PIC {stock.pic_name}</p><p className="num text-sm font-bold">Total Stock Awal {stock.total}</p></div><span className="text-xs text-primary">Detail</span></div></button></Bento>)}{!history.length && <Empty text="Pilih Rider dan periode untuk melihat stock awal." />}{selectedStock && <Dialog open onOpenChange={() => setSelectedStock(null)}><DialogContent data-testid="stock-audit-detail-dialog" className="max-h-[85vh] overflow-y-auto"><DialogHeader><DialogTitle>Detail Stock Awal</DialogTitle></DialogHeader><p className="text-sm">Rider: <b>{selectedStock.rider_name}</b> · PIC: <b>{selectedStock.pic_name}</b></p><p className="num font-bold">Total Stock Awal: {selectedStock.total}</p><div className="space-y-2">{Object.entries(selectedStock.detail || selectedStock.items).map(([name, qty]) => <div key={name} className="flex justify-between text-sm"><span>{name}</span><b>{qty}</b></div>)}</div>{selectedStock.photo && <img src={selectedStock.photo} alt="Bukti foto stock awal" className="w-full rounded-lg" />}{selectedStock.verified_at && <p className="text-emerald-600 text-sm font-bold">✓ Diverifikasi Rider</p>}</DialogContent></Dialog>}</div>;

  const total = Object.values(items).reduce((a, b) => a + b, 0);
  const rider = riders.find((r) => r.id === riderId);

  const save = async () => {
    if (!photo) return toast.error(t("photoRequired"));
    if (busy) return;
    setBusy(true);
    try {
      const { data } = await api.post("/rider-stock", { rider_id: riderId, date, items, photo });
      toast.success(t("save") + " ✓");
      let m = `*SI FOUR AM STOCK REPORT*\n--------------------------------------\n👤 Crew Name: ${rider.name}\n👥 PIC: ${data.pic_name}\n📅 Report Date: ${fmtDate(date)} (${data.time} WIB)\n--------------------------------------\n\n*STOCK DETAILS:*\n`;
      menus.forEach((mn) => { m += `- ${mn.name}: ${items[mn.id] || 0}\n`; });
      m += `\n--------------------------------------\n📊 GRAND TOTAL: ${data.total} Cups\n--------------------------------------\n_(Photo evidence has been uploaded to the system)_\n\n🔥 Keep up the sales! 🚀☕`;
      await shareReceipt(null, m, `stock-${rider.name}-${date}.jpg`, rider.whatsapp);
      api.get("/rider-stock/history", { params: { rider_id: riderId, start: "2000-01-01", end: "2100-01-01" } }).then((r) => setHistory(r.data));
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  const forecast = async () => {
    try {
      const { data } = await api.get("/forecast", { params: { rider_id: riderId, date } });
      const nextItems = {};
      data.items.forEach((item) => { nextItems[item.menu_id] = item.suggested; });
      setItems(nextItems);
      setFc(data);
      const basis = data.basis === "default"
        ? (lang === "id" ? "belum ada riwayat, pakai default" : "no history, defaults")
        : `${data.days_of_history} ${lang === "id" ? "hari riwayat" : "days history"}`;
      toast.success(`🤖 ${data.total} cups · ${basis}${data.factor > 1 ? " · +20% weekend/libur" : ""}`);
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  return (
    <div data-testid="rider-stock-page">
      <PageHeader eyebrow="Stock" title="Stock Awal" />
      <div className="grid lg:grid-cols-3 gap-6">
        <Bento gold className="lg:col-span-2 fade-up" testId="rider-stock-form">
          <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] items-end gap-1.5 mb-5">
            <Field label={`${t("pic")} (auto)`} className="min-w-0"><input data-testid="rider-stock-pic" className="field h-[22px] bg-muted/50 px-1 text-[11px]" value={user.name} readOnly /></Field>
            <Field label={t("selectRider")} className="min-w-0"><Select testId="rider-stock-rider-select" className="h-[22px] px-1 text-[11px]" value={riderId} onChange={setRiderId} placeholder="—" options={riders.map((r) => ({ value: r.id, label: r.name }))} /></Field>
          </div>
          <div className="flex items-end justify-between gap-2 mb-2">
            <div className="flex w-[calc(50%-0.1875rem)] min-w-0 flex-col gap-0.5">
              <span className="text-[10px] font-semibold text-primary">Pilih Tanggal</span>
              <input data-testid="rider-stock-date-input" type="date" aria-label={t("date")} className="field h-[22px] w-full min-w-0 px-1 text-[11px]" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <button data-testid="forecast-button" disabled={!riderId} onClick={forecast} className="btn-ghost h-8 px-3 text-xs"><Sparkles className="w-3 h-3 text-primary" />{lang === "id" ? "Prediksi AI" : "AI Forecast"}</button></div>
          {fc && <p className="text-[11px] text-muted-foreground mb-2" data-testid="forecast-info">{lang === "id" ? "Saran berdasarkan rata-rata hari yang sama (60%) + 14 hari terakhir (40%), buffer 10%" : "Suggestion = same weekday avg (60%) + last 14 days (40%), +10% buffer"}{fc.holiday ? " · 🎉 libur nasional" : fc.weekend ? " · weekend" : ""}</p>}
          <table className="table-x text-xs [&_th]:py-[5px] [&_td]:py-[4px]"><thead><tr><th>#</th><th>{t("menu")}</th>{fc && <th className="hide-xs">AI</th>}<th className="text-right">{t("qty")}</th></tr></thead>
            <tbody>{menus.map((m) => (
              <tr key={m.id}><td className="num text-muted-foreground">{m.order}</td><td><div className="flex items-center justify-between gap-2"><span className="font-semibold">{m.name}</span><span className={`shrink-0 text-[10px] ${m.stock > 0 ? "text-primary" : "text-muted-foreground"}`}>Stok Central ({m.stock})</span></div></td>{fc && <td className="num text-xs text-primary hide-xs">{fc.items.find((i) => i.menu_id === m.id)?.suggested}</td>}
                <td className="text-right"><QtySelect testId={`rider-stock-qty-${m.id}`} max={m.max_stock} value={items[m.id] || 0} onChange={(v) => setItems({ ...items, [m.id]: v })} /></td></tr>))}</tbody>
            <tfoot><tr><td /><td className="font-bold">{t("total")}</td>{fc && <td className="hide-xs" />}<td data-testid="rider-stock-total" className="text-right font-bold num text-xl text-primary">{total}</td></tr></tfoot></table>
        </Bento>
        <div className="space-y-6">
          <Bento className="fade-up" testId="rider-stock-photo-card">
            <p className="eyebrow mb-3">{t("photoEvidence")} *</p>
            <PhotoCapture value={photo} onChange={setPhoto} testId="rider-stock-photo" />
            <button data-testid="rider-stock-save-button" onClick={save} disabled={!riderId || !photo || busy} className="btn-primary w-full mt-4">{t("saveRider")}</button>
            <p className="text-[11px] text-muted-foreground mt-2 text-center">{photo ? "✓" : "!"} {t("photoRequired")} · WhatsApp</p>
          </Bento>
          <Bento className="fade-up" testId="rider-stock-history">
            <p className="eyebrow mb-3">Riwayat Stock</p>
            {history.slice(0, 8).map((h) => <div key={h.id} className="flex items-center gap-3 py-2 border-b border-border/50 text-sm">
              {h.photo ? <img src={h.photo} alt="" className="w-10 h-10 rounded-lg object-cover" /> : <div className="w-10 h-10 rounded-lg bg-muted" />}
              <span className="flex-1">{fmtDate(h.date)} <span className="text-xs text-muted-foreground">{h.time || ""} · {h.pic_name || h.created_by}</span></span><span className="num font-bold">{h.total} cups</span></div>)}
            {!history.length && <Empty text={t("noData")} />}
          </Bento>
        </div>
      </div>
    </div>
  );
}
