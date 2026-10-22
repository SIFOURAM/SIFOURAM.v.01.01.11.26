import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Minus, Plus, Trash2, LogIn, LogOut, ReceiptText, History, Lock, CalendarCheck, Split } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { fmtRp, today, fmtTime, waNumber } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { useAuth } from "../context/AuthContext";
import { useLiveRevision } from "../context/LiveDataContext";
import { PageHeader, Bento, Field, Select, PhotoCapture, ReceiptModal, RLine, Empty, QtySelect } from "../components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import CoachChat from "../components/CoachChat";

const BUNDLES = { 1: { cups: 4, price: 45000 }, 2: { cups: 10, price: 110000 } };
const ORDER_TYPES = [
  { value: "dine_in", label: "Dine In" },
  { value: "takeaway", label: "Takeaway" },
  { value: "online", label: "Online" },
];
const TABLE_OPTIONS = Array.from({ length: 20 }, (_, index) => ({
  value: String(index + 1),
  label: `Meja ${index + 1}`,
}));

function PinGate() {
  const { unlockPos } = useAuth();
  const { t } = useT();
  const [pin, setPin] = useState("");
  const press = async (k) => {
    if (k === "⌫") return setPin(pin.slice(0, -1));
    if (pin.length >= 6) return;
    const p = pin + k;
    setPin(p);
    if (p.length === 6) {
      try { await api.post("/auth/verify-pin", { pin: p }); unlockPos(); toast.success("✓ PIN"); }
      catch (error) { toast.error(errMsg(error)); setPin(""); }
    }
  };
  return (
    <div className="max-w-xs mx-auto text-center pt-10 fade-up" data-testid="pin-gate">
      <p className="eyebrow mb-2">{t("pin")}</p><h2 className="text-2xl font-bold mb-6">{t("enterPin")}</h2>
      <div className="flex justify-center gap-3 mb-8 h-4">{Array.from({ length: 6 }).map((_, i) => <span key={i} className={`w-3 h-3 rounded-full transition-colors ${i < pin.length ? "bg-primary" : "bg-muted"}`} />)}</div>
      <div className="grid grid-cols-3 gap-3">{["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"].map((k, i) => (
        k === "" ? <span key={`b${i}`} /> : <button key={`k${k}`} data-testid={`pin-key-${k === "⌫" ? "del" : k}`} onClick={() => press(k)} className="h-16 rounded-2xl bg-card border border-border text-xl font-heading font-semibold hover:bg-muted active:scale-95 transition-transform">{k}</button>))}</div>
    </div>
  );
}

function Attendance({ rider, riders, riderId, setRiderId, isRider }) {
  const { t } = useT();
  const [att, setAtt] = useState(null);
  const [pin, setPin] = useState("");
  const [photo, setPhoto] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => riderId && api.get("/attendance", { params: { start: today(), end: today(), rider_id: riderId } }).then((r) => setAtt(r.data[0] || null));
  useEffect(() => { load(); }, [riderId]); // eslint-disable-line
  const act = async (kind) => {
    if (!photo) return toast.error(t("photoRequired"));
    if (pin.length !== 6) return toast.error("Masukkan PIN Rider 6 angka.");
    setBusy(true);
    let pos = {};
    try { const p = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 4000 })); pos = { lat: p.coords.latitude, lng: p.coords.longitude }; } catch { }
    try { await api.post(`/attendance/${kind}`, { rider_id: riderId, pin, photo, date: today(), ...pos }); toast.success(kind === "checkin" ? t("checkIn") + " ✓" : t("checkOut") + " ✓"); setPin(""); setPhoto(null); load(); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <Bento gold className="fade-up" testId="attendance-card">
      <p className="eyebrow mb-3">{t("attendance")} · {today()}</p>
      {!isRider && <Field label={t("selectRider")} className="mb-3"><Select testId="pos-rider-select" value={riderId} onChange={setRiderId} placeholder="—" options={riders.map((r) => ({ value: r.id, label: r.name }))} /></Field>}
      {isRider && <p className="font-heading font-bold text-lg mb-3">{rider?.name}</p>}
      {att ? (
        <div className="text-sm space-y-1 mb-3"><p className="flex justify-between"><span className="text-muted-foreground">{t("checkIn")}</span><span className="num font-semibold text-emerald-500">{att.checkin_time || fmtTime(att.checkin_at)}</span></p>
          <p className="flex justify-between"><span className="text-muted-foreground">{t("checkOut")}</span><span className="num font-semibold">{att.checkout_at ? (att.checkout_time || fmtTime(att.checkout_at)) : "—"}</span></p>
          <div className="flex gap-2 pt-1">{att.checkin_photo && <img src={att.checkin_photo} alt="" className="w-14 h-14 rounded-xl object-cover" />}{att.checkout_photo && <img src={att.checkout_photo} alt="" className="w-14 h-14 rounded-xl object-cover" />}</div></div>
      ) : <p className="text-xs text-muted-foreground mb-3">—</p>}
      {(!att || !att.checkout_at) && riderId && (
        <div className="space-y-3">
          <PhotoCapture value={photo} onChange={setPhoto} testId="attendance-photo" />
          <input data-testid="attendance-pin-input" type="password" inputMode="numeric" maxLength="6" className="field" placeholder="PIN Rider (6 angka)" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} />
          {!att ? <button data-testid="checkin-button" disabled={busy || pin.length !== 6 || !photo} onClick={() => act("checkin")} className="btn-primary w-full"><LogIn className="w-4 h-4" />{t("checkIn")}</button>
            : <button data-testid="attendance-checkout-button" disabled={busy} onClick={() => act("checkout")} className="btn-ghost w-full"><LogOut className="w-4 h-4" />{t("checkOut")}</button>}
        </div>)}
    </Bento>
  );
}

function BundlePicker({ b, items12, onAdd, onClose }) {
  const { t } = useT();
  const [sel, setSel] = useState({});
  const need = BUNDLES[b].cups;
  const sum = Object.values(sel).reduce((a, x) => a + x, 0);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="pos-bundle-dialog"><DialogHeader><DialogTitle>BUNDLING {b} · {need} {t("cups")} · {fmtRp(BUNDLES[b].price)}</DialogTitle></DialogHeader>
        {items12.map((i) => <div key={i.menu_id} className="flex items-center justify-between py-1.5 border-b border-border/40 text-sm"><span>{i.name} <span className="text-xs text-muted-foreground">({i.remaining})</span></span><QtySelect testId={`pos-bundle-qty-${i.menu_id}`} max={Math.min(need, i.remaining)} value={sel[i.menu_id] || 0} onChange={(v) => setSel({ ...sel, [i.menu_id]: v })} /></div>)}
        <div className="flex items-center justify-between mt-3"><span className={`num font-bold ${sum === need ? "text-emerald-500" : "text-red-500"}`}>{sum} / {need}</span>
          <button data-testid="pos-bundle-add" disabled={sum !== need} onClick={() => onAdd(Object.fromEntries(Object.entries(sel).filter(([, q]) => q > 0)))} className="btn-primary h-10">{t("save")}</button></div>
      </DialogContent>
    </Dialog>
  );
}

export default function POS() {
  const { user, posUnlocked } = useAuth();
  const { t, lang } = useT();
  const isRider = user.role === "rider";
  const [riders, setRiders] = useState([]);
  const [riderId, setRiderId] = useState(isRider ? user.id : "");
  const [stock, setStock] = useState({ has_stock: false, closed: false, deposited: false, items: [] });
  const [cart, setCart] = useState({});
  const [bcart, setBcart] = useState([]); // [{bundle, components}]
  const [pickB, setPickB] = useState(null);
  const [cust, setCust] = useState({ name: "", phone: "" });
  const [pay, setPay] = useState("cash");
  const [cash, setCash] = useState("");
  const [splitCash, setSplitCash] = useState("");
  const [orderType, setOrderType] = useState("takeaway");
  const [tableNumber, setTableNumber] = useState("");
  const [qrisAccounts, setQrisAccounts] = useState([]);
  const [qrisPreview, setQrisPreview] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [eod, setEod] = useState(null);
  const [hist, setHist] = useState(null);
  const [histDate, setHistDate] = useState(today());
  const [busy, setBusy] = useState(false);
  const [showAbsen, setShowAbsen] = useState(false);
  const [clientId, setClientId] = useState(crypto.randomUUID());
  const revision = useLiveRevision();

  useEffect(() => { if (!isRider) api.get("/users", { params: { role: "rider" } }).then((r) => setRiders(r.data)); }, [isRider, revision]);
  const loadStock = () => riderId && api.get("/pos/stock", { params: { rider_id: riderId, date: today() } }).then((r) => setStock(r.data));
  useEffect(() => { loadStock(); }, [riderId, revision]); // eslint-disable-line
  useEffect(() => {
    api.get("/payment-accounts/public", { params: riderId ? { rider_id: riderId } : {} })
      .then((response) => setQrisAccounts(response.data))
      .catch(() => setQrisAccounts([]));
  }, [riderId]);
  useEffect(() => {
    const p = cust.phone.replace(/\D/g, "");
    if (p.length >= 5 && !cust.name) api.get("/customers/lookup", { params: { phone: p } }).then((r) => { const c = r.data.customers[0]; if (c?.name) setCust((x) => ({ ...x, name: c.name })); });
  }, [cust.phone]); // eslint-disable-line

  const locked = !stock.has_stock || stock.closed || stock.deposited;
  const need = useMemo(() => { const n = { ...cart }; bcart.forEach((b) => Object.entries(b.components).forEach(([m, q]) => { n[m] = (n[m] || 0) + q; })); return n; }, [cart, bcart]);
  const lines = useMemo(() => stock.items.filter((i) => cart[i.menu_id]).map((i) => ({ ...i, qty: cart[i.menu_id], sub: cart[i.menu_id] * i.price })), [cart, stock]);
  const total = lines.reduce((s, l) => s + l.sub, 0) + bcart.reduce((s, b) => s + BUNDLES[b.bundle].price, 0);
  const cups = Object.values(need).reduce((a, x) => a + x, 0);
  const change = pay === "cash" ? Math.max(0, Number(cash || 0) - total) : 0;
  const splitCashAmount = Number(splitCash || 0);
  const splitQrisAmount = Math.max(0, total - splitCashAmount);
  const splitValid = splitCashAmount > 0 && splitCashAmount < total;

  const add = (i, d = 1) => {
    const q = (cart[i.menu_id] || 0) + d;
    if ((need[i.menu_id] || 0) + d > i.remaining) return toast.warning(`${i.name}: ${i.remaining} ${t("remaining").toLowerCase()}`);
    setCart({ ...cart, [i.menu_id]: Math.max(0, q) });
  };
  const addBundle = (comps) => {
    for (const [m, q] of Object.entries(comps)) { const it = stock.items.find((x) => x.menu_id === m); if ((need[m] || 0) + q > it.remaining) return toast.warning(`${it.name}: ${it.remaining} ${t("remaining").toLowerCase()}`); }
    setBcart([...bcart, { bundle: pickB, components: comps }]); setPickB(null);
  };
  const checkout = async () => {
    if ((!lines.length && !bcart.length) || busy) return;
    if (locked) return toast.error("Pembayaran tidak dapat dilakukan sebelum stok awal terverifikasi.");
    if (orderType === "dine_in" && !tableNumber) return toast.error("Pilih nomor meja terlebih dahulu.");
    if (pay === "cash" && Number(cash) < total) return toast.error(t("cashReceived") + " < " + t("total"));
    if (pay === "split" && !splitValid) return toast.error("Nominal tunai split harus lebih dari Rp 0 dan kurang dari total.");
    setBusy(true);
    try {
      const items = [...lines.map((l) => ({ menu_id: l.menu_id, qty: l.qty })), ...bcart.map((b) => ({ bundle: b.bundle, qty: 1, components: b.components }))];
      const paymentParts = pay === "split"
        ? [
          { method: "cash", amount: splitCashAmount },
          { method: "qris", amount: splitQrisAmount },
        ]
        : [];
      const { data } = await api.post("/sales", {
        rider_id: riderId,
        date: today(),
        customer_name: cust.name,
        customer_phone: cust.phone,
        items,
        payment_method: pay,
        payment_parts: paymentParts,
        cash_received: pay === "cash" ? Number(cash || 0) : splitCashAmount,
        order_type: orderType,
        table_number: orderType === "dine_in" ? tableNumber : "",
        client_id: clientId,
      });
      setReceipt(data);
      setCart({});
      setBcart([]);
      setCash("");
      setSplitCash("");
      setCust({ name: "", phone: "" });
      setOrderType("takeaway");
      setTableNumber("");
      setClientId(crypto.randomUUID());
      loadStock();
      toast.success(data.receipt_no);
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const openEod = () => api.get("/sales/eod", { params: { rider_id: riderId, date: today() } }).then((r) => setEod(r.data));
  const closeEod = async () => { try { const { data } = await api.post("/sales/eod/close", { rider_id: riderId, date: today() }); if (user.role === "rider") { window.dispatchEvent(new CustomEvent("si4am-eod-closed", { detail: { sessionEndsAt: data.session_ends_at } })); } setEod(data); loadStock(); toast.success(t("eodDone")); } catch (e) { toast.error(errMsg(e)); } };
  const openHist = () => api.get("/sales", { params: { start: histDate, end: histDate, rider_id: riderId } }).then((r) => setHist(r.data));
  useEffect(() => { if (hist) openHist(); }, [histDate]); // eslint-disable-line

  if (!posUnlocked) return <PinGate />;
  const rider = isRider ? user : riders.find((r) => r.id === riderId);
  const L = lang === "id";
  const shouldHideCoach = lines.length > 0 || bcart.length > 0 || !!receipt || !!qrisPreview || busy;
  const receiptOrder = receipt && [
    receipt.order_type === "dine_in" ? "Dine In" : receipt.order_type === "online" ? "Online" : "Takeaway",
    receipt.table_number ? `Meja ${receipt.table_number}` : null,
  ].filter(Boolean).join(" · ");
  const receiptPaymentText = receipt && (receipt.payment_parts || []).map((part) => (
    `${part.method.toUpperCase()}: ${fmtRp(part.amount)}`
  )).join("\n");
  const receiptText = receipt && `*SI FOUR AM — ${L ? "STRUK" : "RECEIPT"}*\n🧾 ${receipt.receipt_no}\n📅 ${receipt.date} ${receipt.time || ""}\n👤 ${receipt.customer_name || t("customer")}\n🛵 ${receipt.rider_name}\n----------------------------------\n` +
    `${receiptOrder ? `🍽️ ${receiptOrder}\n` : ""}` +
    receipt.items.map((i) => `${i.name} x${i.qty} = ${fmtRp(i.subtotal)}` + (i.component_names ? `\n   (${Object.entries(i.component_names).map(([n, q]) => `${n} ${q}`).join(", ")})` : "")).join("\n") +
    `\n----------------------------------\n💰 Total: ${fmtRp(receipt.total)}\n${receiptPaymentText || receipt.payment_method.toUpperCase()}${receipt.change ? `\n🔁 ${t("change")}: ${fmtRp(receipt.change)}` : ""}\n\n${t("thankYou")} ☕`;
  const formatQty = (value) => Number.isInteger(value) ? value : Number(value || 0).toFixed(2);
  const eodText = eod && `*SI FOUR AM — ${L ? "TUTUP HARIAN" : "END OF DAY"}*\n🛵 ${rider?.name}\n📅 ${eod.date}\n----------------------------------\n` +
    eod.rows.map((r) => `${r.name}: awal ${r.initial} | sisa ${r.remaining} | cash ${formatQty(r.cash_qty)} | qris ${formatQty(r.qris_qty)}`).join("\n") +
    `\n----------------------------------\n☕ ${t("totalSold")}: ${eod.total_cups} cups\n💰 Cash: ${fmtRp(eod.total_cash)}\n💳 QRIS: ${fmtRp(eod.total_qris)}\n🚀 Total: ${fmtRp(eod.total)}`;
  const histRows = hist && stock.items.map((i) => {
    let c = 0;
    let q = 0;
    let split = 0;
    hist.forEach((h) => h.items.forEach((it) => {
      const quantity = it.components ? it.components[i.menu_id] || 0 : it.menu_id === i.menu_id ? it.qty : 0;
      if (h.payment_method === "cash") c += quantity;
      else if (h.payment_method === "qris") q += quantity;
      else split += quantity;
    }));
    return { ...i, c, q, split };
  });

  return (
    <div data-testid="pos-page">
      <PageHeader eyebrow="Point of Sale" title={t("pos")}>
        <div className="flex flex-col items-stretch sm:items-end gap-2 w-full sm:w-auto">
          <button data-testid="absen-button" onClick={() => setShowAbsen(true)} className="btn-primary h-10"><CalendarCheck className="w-4 h-4" />{L ? "Absen" : "Attendance"}</button>
          <div className="flex gap-2">
            <button data-testid="eod-button" onClick={openEod} disabled={!riderId} className="btn-ghost h-9 text-xs flex-1"><ReceiptText className="w-4 h-4" />{t("endDay")}</button>
            <button data-testid="history-button" onClick={openHist} disabled={!riderId} className="btn-ghost h-9 text-xs flex-1"><History className="w-4 h-4" />{t("history")}</button>
          </div>
        </div>
      </PageHeader>
      <div className="grid gap-6">
        {!isRider && !riderId && <div className="rounded-2xl border border-primary/40 bg-primary/10 p-4 text-sm text-primary flex gap-2" data-testid="pick-rider-hint"><CalendarCheck className="w-4 h-4 shrink-0" />{L ? "Klik tombol Absen untuk memilih rider dan melakukan absensi." : "Click Attendance to select a rider."}</div>}
        <div className="space-y-6">
          {riderId && !stock.has_stock && <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-500 flex gap-2" data-testid="no-stock-warning"><Lock className="w-4 h-4 shrink-0" />{stock.pending_stock ? "Stok awal sudah disiapkan dan menunggu verifikasi Rider sebelum kasir dibuka." : t("noStock")}</div>}
          {riderId && stock.has_stock && (stock.closed || stock.deposited) && <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-500 flex gap-2" data-testid="pos-locked"><Lock className="w-4 h-4 shrink-0" />{stock.deposited ? t("depositDone") : t("eodDone")}</div>}
          {riderId && <>
            <Bento gold className="fade-up py-4" testId="daily-target">
              {(() => { const sold = stock.items.reduce((s, i) => s + i.sold, 0); const tgt = 50; const pct = Math.min(100, Math.round((sold / tgt) * 100)); const lvl = sold >= 50 ? "🏆" : sold >= 31 ? "🚀" : "💪";
                return <><div className="flex justify-between items-end mb-2"><div><p className="eyebrow">{L ? "Target Harian" : "Daily Target"} {lvl}</p><p className="text-2xl font-bold num font-heading">{sold} <span className="text-sm text-muted-foreground">/ {tgt} {t("cups")}</span></p></div><p className="text-xs text-muted-foreground text-right">{sold < 31 ? `${31 - sold} → 🚀` : sold < 50 ? `${50 - sold} → 🏆` : (L ? "Target tercapai!" : "Target smashed!")}</p></div>
                  <div className="h-2.5 rounded-full bg-muted overflow-hidden"><div className="h-full rounded-full bg-gradient-to-r from-primary to-[#F97316] transition-all duration-700" style={{ width: `${pct}%` }} /></div></>; })()}
            </Bento>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3" data-testid="product-grid">
              {stock.items.map((i) => (
                <button key={i.menu_id} data-testid={`pos-product-${i.menu_id}`} onClick={() => add(i)} disabled={locked || i.remaining <= 0}
                  className={`bento p-0 text-left overflow-hidden group active:scale-[0.98] transition-transform disabled:opacity-40 ${cart[i.menu_id] ? "gold" : ""}`}>
                  <div className="h-20 bg-muted relative">{i.photo && <img src={i.photo} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />}
                    <span className={`absolute top-2 right-2 text-[10px] font-bold px-2 py-0.5 rounded-full ${i.remaining <= 3 ? "bg-red-500 text-white" : "bg-black/60 text-white"}`}>{i.remaining}</span>
                    {cart[i.menu_id] > 0 && <span className="absolute bottom-2 left-2 w-7 h-7 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">{cart[i.menu_id]}</span>}</div>
                  <div className="p-3"><p className="text-xs font-heading font-bold leading-tight">{i.name}</p><p className="text-xs text-primary num font-semibold mt-1">{fmtRp(i.price)}</p>
                    {i.remaining > 0 && i.remaining <= 3 && <p className="text-[10px] text-red-500 font-semibold">{t("lowStock")}</p>}</div>
                </button>))}
              {[1, 2].map((b) => <button key={b} data-testid={`pos-bundle-${b}`} disabled={locked} onClick={() => setPickB(b)} className="bento gold p-4 text-left disabled:opacity-40"><p className="eyebrow text-primary">{t("bundling")} {b}</p><p className="font-heading font-bold text-sm mt-1">{BUNDLES[b].cups} {t("cups")} Rp 12K</p><p className="text-primary num font-bold text-sm">{fmtRp(BUNDLES[b].price)}</p></button>)}
            </div>
            <Bento gold className="fade-up" testId="cart-panel">
              <p className="eyebrow mb-3">{t("checkout")}</p>
              {lines.map((l) => (
                <div key={l.menu_id} className="flex items-center justify-between py-2 border-b border-border/50 text-sm">
                  <span className="font-medium flex-1 truncate">{l.name}</span>
                  <div className="flex items-center gap-2"><button data-testid={`cart-minus-${l.menu_id}`} onClick={() => add(l, -1)} className="w-7 h-7 rounded-full bg-muted flex items-center justify-center"><Minus className="w-3 h-3" /></button>
                    <span className="num w-6 text-center font-bold">{l.qty}</span><button data-testid={`cart-plus-${l.menu_id}`} onClick={() => add(l, 1)} className="w-7 h-7 rounded-full bg-muted flex items-center justify-center"><Plus className="w-3 h-3" /></button></div>
                  <span className="num w-24 text-right">{fmtRp(l.sub)}</span></div>))}
              {bcart.map((b, i) => <div key={i} className="flex items-center justify-between py-2 border-b border-border/50 text-sm" data-testid={`cart-bundle-${i}`}>
                <span className="flex-1"><b className="text-primary">BUNDLING {b.bundle}</b><span className="block text-[10px] text-muted-foreground">{Object.entries(b.components).map(([m, q]) => `${stock.items.find((x) => x.menu_id === m)?.name} ×${q}`).join(", ")}</span></span>
                <button onClick={() => setBcart(bcart.filter((_, j) => j !== i))} className="w-7 h-7 rounded-full bg-muted flex items-center justify-center mr-2"><Trash2 className="w-3 h-3" /></button><span className="num w-24 text-right">{fmtRp(BUNDLES[b.bundle].price)}</span></div>)}
              {!lines.length && !bcart.length && <Empty text={t("tapProducts")} />}
              <div className="mt-4">
                <p className="eyebrow mb-2">Tipe pesanan</p>
                <div className="grid grid-cols-3 gap-2" data-testid="order-type-selector">
                  {ORDER_TYPES.map((type) => (
                    <button
                      key={type.value}
                      data-testid={`order-type-${type.value}`}
                      onClick={() => {
                        setOrderType(type.value);
                        if (type.value !== "dine_in") setTableNumber("");
                      }}
                      className={`h-10 rounded-lg text-xs font-bold ${
                        orderType === type.value ? "bg-primary text-white" : "bg-muted"
                      }`}
                    >
                      {type.label}
                    </button>
                  ))}
                </div>
                {orderType === "dine_in" && (
                  <div className="mt-3">
                    <Field label="Pilih Meja">
                      <Select
                        testId="pos-table-select"
                        value={tableNumber}
                        onChange={setTableNumber}
                        placeholder="Pilih nomor meja"
                        options={TABLE_OPTIONS}
                      />
                    </Field>
                  </div>
                )}
              </div>
              <div className="grid sm:grid-cols-2 gap-3 mt-4">
                <input data-testid="customer-phone-input" className="field" placeholder="WhatsApp 08xx" value={cust.phone} onChange={(e) => setCust({ ...cust, phone: e.target.value })} />
                <input data-testid="customer-name-input" className="field" placeholder={t("customer")} value={cust.name} onChange={(e) => setCust({ ...cust, name: e.target.value })} />
                <div className="flex gap-2">
                  {["cash", "qris", "split"].map((p) => (
                    <button
                      key={p}
                      data-testid={`pay-${p}`}
                      aria-label={p === "split" ? "Split payment" : p}
                      onClick={() => setPay(p)}
                      className={`flex-1 h-10 rounded-lg text-xs font-bold uppercase ${
                        pay === p ? "bg-primary text-white" : "bg-muted"
                      }`}
                    >
                      {p === "split" ? <span className="flex items-center justify-center gap-1"><Split className="w-3.5 h-3.5" />Split</span> : p}
                    </button>
                  ))}
                </div>
                {pay === "cash" && <input data-testid="cash-received-input" type="number" className="field num" placeholder={t("cashReceived")} value={cash} onChange={(e) => setCash(e.target.value)} />}
                {pay === "qris" && qrisAccounts.map((account) => (
                  <div key={account.id} data-testid={`pos-qris-${account.id}`} className="sm:col-span-2 flex items-center gap-3 rounded-lg border border-primary/30 p-3">
                    <button data-testid={`pos-qris-open-${account.id}`} onClick={() => setQrisPreview(account)} className="shrink-0"><img src={account.qris_photo} alt={`QRIS ${account.name}`} className="w-36 h-36 object-contain bg-white rounded" /></button>
                    <div><p className="font-semibold text-sm">{account.name}</p><p className="text-xs text-muted-foreground">Scan QRIS untuk pembayaran</p></div>
                  </div>
                ))}
                {pay === "split" && (
                  <div className="grid grid-cols-2 gap-2 sm:col-span-2" data-testid="split-payment-panel">
                    <input
                      data-testid="split-cash-input"
                      type="number"
                      className="field num"
                      placeholder="Tunai"
                      min="1"
                      max={Math.max(0, total - 1)}
                      value={splitCash}
                      onChange={(e) => setSplitCash(e.target.value)}
                    />
                    <div data-testid="split-qris-amount" className="field flex items-center num text-muted-foreground">
                      QRIS: {fmtRp(splitQrisAmount)}
                    </div>
                  </div>
                )}
              </div>
              {pay === "split" && !splitValid && (
                <p data-testid="split-payment-hint" className="mt-2 text-xs text-amber-300">
                  Isi nominal tunai. Sisa total otomatis dibayar QRIS.
                </p>
              )}
              <div className="flex items-end justify-between mt-5">
                <div><p className="eyebrow">{t("total")} · {cups} {t("cups")}</p><p data-testid="cart-total" className="text-3xl font-bold num font-heading">{fmtRp(total)}</p>
                  {pay === "cash" && cash && <p data-testid="cart-change" className="text-sm text-emerald-500 num">{t("change")}: {fmtRp(change)}</p>}</div>
                <div className="flex gap-2"><button data-testid="cart-clear" onClick={() => { setCart({}); setBcart([]); }} className="btn-ghost h-11 w-11 p-0"><Trash2 className="w-4 h-4" /></button>
                  <button data-testid="checkout-button" onClick={checkout} disabled={locked || busy || (!lines.length && !bcart.length) || (orderType === "dine_in" && !tableNumber) || (pay === "cash" && Number(cash) < total) || (pay === "split" && !splitValid)} className="btn-primary">{t("checkout")}</button></div>
              </div>
            </Bento>
          </>}
        </div>
      </div>

      {pickB && <BundlePicker b={pickB} items12={stock.items.filter((i) => i.price === 12000)} onAdd={addBundle} onClose={() => setPickB(null)} />}

      <ReceiptModal open={!!receipt} onClose={() => setReceipt(null)} title={L ? "Struk Pembayaran" : "Payment Receipt"} waText={receiptText} waPhone={receipt?.customer_phone} filename={`${receipt?.receipt_no}.png`} autoShot={false} testId="sale-receipt">
        {receipt && <>
          <RLine l="No" r={receipt.receipt_no} /><RLine l={t("date")} r={`${receipt.date} ${receipt.time || ""}`} /><RLine l="Rider" r={receipt.rider_name} /><RLine l={t("customer")} r={receipt.customer_name || "-"} />
          <div className="border-t border-dashed border-gray-300 my-2" />
          {receipt.items.map((i, k) => <div key={k}><RLine l={`${i.name} x${i.qty}`} r={fmtRp(i.subtotal)} />{i.component_names && <p className="text-[10px] text-gray-500 pl-2">{Object.entries(i.component_names).map(([n, q]) => `${n} ×${q}`).join(", ")}</p>}</div>)}
          <div className="border-t border-dashed border-gray-300 my-2" />
          <RLine bold l="TOTAL" r={fmtRp(receipt.total)} />
          {(receipt.payment_parts || []).map((part) => (
            <RLine key={part.method} l={part.method.toUpperCase()} r={fmtRp(part.amount)} />
          ))}
          {!receipt.payment_parts?.length && <RLine l={receipt.payment_method.toUpperCase()} r={fmtRp(receipt.total)} />}
          {receipt.change > 0 && <RLine l={t("change")} r={fmtRp(receipt.change)} />}
          <RLine l="Pesanan" r={receiptOrder} />
          {receipt.customer_phone && <p className="text-[10px] text-gray-400 mt-2 text-center">wa.me/{waNumber(receipt.customer_phone)}</p>}
        </>}
      </ReceiptModal>

      <ReceiptModal open={!!eod} onClose={() => setEod(null)} title={L ? "Laporan Tutup Harian" : "End of Day Report"} waText={eodText} filename={`EOD-${rider?.name}-${today()}.png`} autoShot={false} testId="eod-receipt">
        {eod && <>
          <RLine l="Rider" r={rider?.name} /><RLine l={t("date")} r={eod.date} /><RLine l={t("transactions")} r={eod.transactions} />
          <div className="border-t border-dashed border-gray-300 my-2" />
          <div className="grid grid-cols-6 text-[10px] font-bold text-gray-500 pb-1"><span className="col-span-2">Menu</span><span className="text-right">Awal</span><span className="text-right">Sisa</span><span className="text-right">Cash</span><span className="text-right">QRIS</span></div>
          {eod.rows.map((r) => <div key={r.menu_id} className="grid grid-cols-6 text-[11px] py-0.5"><span className="col-span-2 truncate">{r.name}</span><span className="text-right num">{r.initial}</span><span className="text-right num">{r.remaining}</span><span className="text-right num">{r.cash_qty}</span><span className="text-right num">{r.qris_qty}</span></div>)}
          <div className="border-t border-dashed border-gray-300 my-2" />
          <RLine l={t("totalSold")} r={`${eod.total_cups} cups`} /><RLine l="Cash" r={fmtRp(eod.total_cash)} /><RLine l="QRIS" r={fmtRp(eod.total_qris)} /><RLine bold l="TOTAL" r={fmtRp(eod.total)} />
          {!eod.closed && <button data-testid="eod-close-button" onClick={closeEod} className="btn-primary w-full mt-3 h-10">{t("endDay")} ✓</button>}
          {eod.closed && <p className="text-[11px] text-center mt-3 text-emerald-600 font-bold">✓ {t("eodDone")}</p>}
        </>}
      </ReceiptModal>

      {hist && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-end sm:items-center justify-center p-4" onClick={() => setHist(null)}>
          <div onClick={(e) => e.stopPropagation()} className="bento gold w-full max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="sales-history-modal">
            <div className="flex items-center justify-between mb-4"><p className="font-heading font-bold">{t("history")}</p><input data-testid="history-date-input" type="date" className="field h-9 w-40" value={histDate} onChange={(e) => setHistDate(e.target.value)} /></div>
            <div className="grid grid-cols-3 gap-2 mb-4 text-center">
              <div className="rounded-xl bg-muted p-3"><p className="eyebrow">Trx</p><p className="font-bold num">{hist.length}</p></div>
              <div className="rounded-xl bg-muted p-3"><p className="eyebrow">{t("revenue")}</p><p className="font-bold num text-xs">{fmtRp(hist.reduce((s, h) => s + h.total, 0))}</p></div>
              <div className="rounded-xl bg-muted p-3"><p className="eyebrow">{t("estProfit")}</p><p className="font-bold num text-xs text-emerald-500">{fmtRp(hist.reduce((s, h) => s + h.total, 0) - histRows.reduce((s, r) => s + (r.c + r.q) * (r.cost || 0), 0))}</p></div>
            </div>
            <table className="table-x mb-4"><thead><tr><th>{t("menu")}</th><th>{t("stock")}</th><th>Cash</th><th>QRIS</th><th>Split</th></tr></thead>
              <tbody>{histRows.map((r) => <tr key={r.menu_id}><td className="text-xs font-semibold">{r.name}</td><td className="num">{r.initial}</td><td className="num">{r.c}</td><td className="num">{r.q}</td><td className="num">{r.split}</td></tr>)}</tbody></table>
            {hist.map((h) => <div key={h.id} className="flex justify-between text-sm py-2 border-b border-border/50"><button data-testid={`hist-receipt-${h.id}`} onClick={() => setReceipt(h)} className="text-left"><span className="num text-xs text-primary underline">{h.receipt_no}</span> <span className="text-xs text-muted-foreground">{h.time}</span> · {h.customer_name || "—"} · {h.cups} {t("cups")}</button><span className="num font-semibold">{fmtRp(h.total)} <span className="text-[10px] uppercase text-muted-foreground">{h.payment_method}</span></span></div>)}
            {!hist.length && <Empty text={t("noData")} />}
          </div>
        </div>)}
      {(user.role === "rider" || user.role === "owner") && <CoachChat hidden={shouldHideCoach} />}

      <Dialog open={showAbsen} onOpenChange={(o) => !o && setShowAbsen(false)}>
        <DialogContent data-testid="absen-dialog"><DialogHeader><DialogTitle>{L ? "Absen Kehadiran" : "Attendance"}</DialogTitle></DialogHeader>
          <Attendance rider={rider} riders={riders} riderId={riderId} setRiderId={setRiderId} isRider={isRider} />
        </DialogContent>
      </Dialog>
      <Dialog open={!!qrisPreview} onOpenChange={() => setQrisPreview(null)}><DialogContent data-testid="pos-qris-preview" className="max-w-sm"><DialogHeader><DialogTitle>QRIS · {qrisPreview?.name}</DialogTitle></DialogHeader>{qrisPreview && <img src={qrisPreview.qris_photo} alt={`QRIS ${qrisPreview.name}`} className="w-full aspect-square object-contain bg-white rounded-lg p-3" />}</DialogContent></Dialog>
    </div>
  );
}
