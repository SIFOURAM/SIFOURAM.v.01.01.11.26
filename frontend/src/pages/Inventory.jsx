import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { MessageCircle, FileDown, Plus } from "lucide-react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { api, errMsg } from "../lib/api";
import { fmtRp, today, openWA, fmtDate, nowTime } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { PageHeader, Bento, Field, Select, PhotoCapture } from "../components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";

const packs = (m) => (m.stock / m.pack_qty).toFixed(2);

export default function Inventory() {
  const { t } = useT();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mats, setMats] = useState([]);
  const [menus, setMenus] = useState([]);
  const [tx, setTx] = useState([]);
  const tab = searchParams.get("tab") || "stock";
  const [openRecipe, setOpenRecipe] = useState(null);
  const [form, setForm] = useState({ material_id: "", type: "in", qty: "", note: "", date: today(), item_name: "", supplier: "" });
  const [newMat, setNewMat] = useState(null);
  const [wf, setWf] = useState({ menu_id: "", qty: "", note: "", photo: "" });
  const submitWastage = async () => {
    try {
      const { data } = await api.post("/inventory/wastage", { menu_id: wf.menu_id, qty: Number(wf.qty), photo: wf.photo, note: wf.note });
      const back = process.env.REACT_APP_BACKEND_URL || "";
      const url = data.photo_url?.startsWith("http") ? data.photo_url : back + data.photo_url;
      openWA(`*SI FOUR AM — WASTAGE MENU*\n📅 ${data.date} ${data.time}\n----------------------------------\n☕ ${data.menu_name}: -${data.qty} cup\nStok: ${data.before} → ${data.after}\n📝 ${data.note || "-"}\n👤 ${data.user}\n📷 Foto: ${url}`);
      toast.success("Wastage dicatat ✓"); setWf({ menu_id: "", qty: "", note: "", photo: "" }); load();
    } catch (e) { toast.error(errMsg(e)); }
  };

  const load = () => Promise.all([api.get("/materials"), api.get("/menus"), api.get("/inventory/tx")]).then(([a, b, c]) => { setMats(a.data); setMenus(b.data); setTx(c.data); });
  useEffect(() => { load(); }, []);

  const submitTx = async (e) => {
    e.preventDefault();
    try { await api.post("/inventory/tx", { ...form, qty: Number(form.qty) }); toast.success("Inventory updated"); setForm({ ...form, qty: "", note: "" }); load(); }
    catch (err) { toast.error(errMsg(err)); }
  };
  const saveMat = async (e) => {
    e.preventDefault();
    try { await api.post("/materials", { ...newMat, pack_qty: Number(newMat.pack_qty), pack_price: Number(newMat.pack_price) }); toast.success("Material created"); setNewMat(null); load(); }
    catch (err) { toast.error(errMsg(err)); }
  };

  const low = mats.filter((m) => m.stock <= m.min_stock);
  const stockText = () => `*SI FOUR AM — STOCK REPORT*\n📅 ${today()}\n----------------------------------\n` +
    mats.map((m) => `${m.stock <= m.min_stock ? "⚠️" : "✅"} ${m.name}: ${Math.round(m.stock)} ${m.unit} (${packs(m)} ${m.pack_label})`).join("\n");
  const orderText = () => `*SI FOUR AM — ORDER ITEMS*\n📅 ${today()}\n----------------------------------\n` +
    (low.length ? low.map((m) => `🛒 ${m.name}: ${Math.max(1, Math.ceil((m.pack_qty * 2 - m.stock) / m.pack_qty))} ${m.pack_label} @ ${fmtRp(m.pack_price)}`).join("\n") : "All items sufficient ✅") +
    `\n----------------------------------\n💰 Est. total: ${fmtRp(low.reduce((s, m) => s + Math.max(1, Math.ceil((m.pack_qty * 2 - m.stock) / m.pack_qty)) * m.pack_price, 0))}`;

  const pdf = (title, head, body) => {
    const doc = new jsPDF({ orientation: "landscape" });
    const stamp = `${fmtDate(today())} ${nowTime()} WIB`;
    doc.setFontSize(15); doc.text(`SI FOUR AM — ${title}`, 14, 14); doc.setFontSize(9); doc.text(stamp, 14, 20);
    autoTable(doc, { startY: 25, head: [head], body, styles: { fontSize: 8, cellPadding: 2, lineWidth: 0.1, lineColor: [180, 180, 180] }, headStyles: { fillColor: [255, 107, 0] }, theme: "grid" });
    doc.save(`si4am-${title.toLowerCase().replace(/\s/g, "-")}-${today()}.pdf`);
  };
  const stockRows = () => mats.map((m) => [m.name, m.category, `${Math.round(m.stock).toLocaleString()} ${m.unit}`, `${packs(m)} ${m.pack_label}`, `${m.pack_qty} ${m.unit}`, fmtRp(m.pack_price), fmtRp((m.stock / m.pack_qty) * m.pack_price), m.stock <= m.min_stock ? "LOW" : "OK"]);
  const orderRows = () => low.map((m) => { const n = Math.max(1, Math.ceil((m.pack_qty * 2 - m.stock) / m.pack_qty)); return [m.name, `${Math.round(m.stock)} ${m.unit}`, `${n} ${m.pack_label}`, fmtRp(m.pack_price), fmtRp(n * m.pack_price)]; });

  return (
    <div data-testid="inventory-page">
      <PageHeader eyebrow="Bar Team" title={t("inventory")}>
        <div className="mr-auto flex flex-wrap items-center gap-2">
          <button data-testid="wa-stock-button" onClick={() => { pdf("Stock Report", ["Material", "Category", "Stock", "Packs", "Pack size", "Pack price", "Stock value", "Status"], stockRows()); openWA(stockText()); }} className="btn-wa h-10"><MessageCircle className="w-4 h-4" />{t("stockReport")}</button>
          <button data-testid="wa-order-button" onClick={() => { pdf("Order Items", ["Material", "Current stock", "Order qty", "Pack price", "Total"], orderRows()); openWA(orderText()); }} className="btn-wa h-10"><FileDown className="w-4 h-4" />PO</button>
        </div>
      </PageHeader>

      {tab === "stock" && (
        <div className="grid lg:grid-cols-3 gap-6">
          <Bento gold className="lg:col-span-1 fade-up" testId="inventory-tx-form">
            <p className="eyebrow mb-4">Receive / Use / Stock Opname</p>
            <form onSubmit={submitTx} className="space-y-3">
              <Field label="Material"><Select testId="tx-material-select" value={form.material_id} onChange={(v) => setForm({ ...form, material_id: v })} placeholder="Select material" options={mats.map((m) => ({ value: m.id, label: `${m.name} (${m.unit})` }))} /></Field>
              <Field label="Type"><Select testId="tx-type-select" value={form.type} onChange={(v) => setForm({ ...form, type: v })} options={[{ value: "in", label: "IN — Receiving" }, { value: "out", label: "OUT — Usage" }, { value: "opname", label: "OPNAME — Set actual" }]} /></Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label={`Qty (${mats.find((m) => m.id === form.material_id)?.unit || "unit"})`}><input data-testid="tx-qty-input" type="number" step="any" className="field" value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} required /></Field>
                <Field label={t("date")}><input data-testid="tx-date-input" type="date" className="field" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></Field>
              </div>
              {form.type === "in" && <div className="grid grid-cols-2 gap-3">
                <Field label="Purchased item / brand"><input data-testid="tx-item-input" className="field" value={form.item_name} onChange={(e) => setForm({ ...form, item_name: e.target.value })} placeholder="e.g. Kopi Arabica 1kg" /></Field>
                <Field label="Supplier / store"><input data-testid="tx-supplier-input" className="field" value={form.supplier} onChange={(e) => setForm({ ...form, supplier: e.target.value })} /></Field></div>}
              <Field label={t("note")}><input data-testid="tx-note-input" className="field" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></Field>
              <button data-testid="tx-submit-button" className="btn-primary w-full" disabled={!form.material_id}>{t("save")}</button>
            </form>
            <button data-testid="new-material-button" onClick={() => setNewMat({ name: "", unit: "g", pack_qty: "", pack_price: "", pack_label: "pack", category: "raw" })} className="btn-ghost w-full mt-3"><Plus className="w-4 h-4" />New material</button>
          </Bento>
          <Bento className="lg:col-span-2 fade-up" testId="inventory-table">
            <p className="eyebrow mb-4">{t("stock")}</p>
            <table className="table-x"><thead><tr><th>{t("material")}</th><th>{t("stock")}</th><th className="hide-xs">Packs</th><th className="hide-sm">Pack</th><th>{t("status")}</th></tr></thead>
              <tbody>{mats.map((m) => (
                <tr key={m.id} data-testid={`material-row-${m.id}`}><td className="font-semibold">{m.name}<span className="block text-[10px] text-muted-foreground uppercase">{m.category}</span></td>
                  <td className="num">{Math.round(m.stock).toLocaleString()} {m.unit}</td><td className="num hide-xs">{packs(m)} {m.pack_label}</td>
                  <td className="num text-muted-foreground hide-sm">{m.pack_qty.toLocaleString()} {m.unit} · {fmtRp(m.pack_price)}</td>
                  <td>{m.stock <= m.min_stock ? <button data-testid={`request-purchase-${m.id}`} onClick={() => navigate(`/purchase-orders?material_id=${m.id}`)} className="text-xs font-semibold text-red-500 hover:underline">{t("lowStock")}</button> : <span className="text-xs text-emerald-500">OK</span>}</td></tr>))}</tbody></table>
          </Bento>
        </div>
      )}

      {tab === "recipes" && (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {menus.map((m) => (
            <Bento key={m.id} className="fade-up" testId={`recipe-card-${m.id}`}>
              <button data-testid={`recipe-toggle-${m.id}`} onClick={() => setOpenRecipe(openRecipe === m.id ? null : m.id)} className="w-full text-left">
                <div className="flex justify-between items-start"><div><p className="font-heading font-bold">{m.name}</p><p className="text-xs text-muted-foreground">Sell {fmtRp(m.price)}</p></div>
                  <div className="text-right"><p className="eyebrow">HPP</p><p className="num font-bold text-primary">{fmtRp(m.cost)}</p><p className="text-[10px] text-emerald-500 num">margin {fmtRp(m.margin)}</p></div></div>
              </button>
              {openRecipe === m.id && <ul data-testid={`recipe-detail-${m.id}`} className="text-xs space-y-1 mt-3 pt-3 border-t border-border/50">{m.recipe.map((r, i) => <li key={i} className="flex justify-between"><span>{r.name}</span><span className="num text-muted-foreground">{r.qty} {r.unit}</span></li>)}
                <li className="flex justify-between text-muted-foreground pt-1 border-t border-border/50"><span>{m.recipe.length} {t("items")} incl. packaging</span></li></ul>}
            </Bento>))}
        </div>
      )}

      {tab === "wastage" && (
        <div className="grid lg:grid-cols-2 gap-6">
          <Bento gold className="fade-up" testId="wastage-form">
            <p className="eyebrow mb-4">Wastage Menu (Center Produksi)</p>
            <div className="space-y-3">
              <Field label="Menu"><Select testId="wastage-menu-select" value={wf.menu_id} onChange={(v) => setWf({ ...wf, menu_id: v })} placeholder="Pilih menu" options={menus.map((m) => ({ value: m.id, label: `${m.name} (stok ${m.stock || 0})` }))} /></Field>
              <Field label="Qty (cup)"><input data-testid="wastage-qty-input" type="number" className="field" value={wf.qty} onChange={(e) => setWf({ ...wf, qty: e.target.value })} /></Field>
              <Field label={t("note")}><input data-testid="wastage-note-input" className="field" value={wf.note} onChange={(e) => setWf({ ...wf, note: e.target.value })} /></Field>
              <div><p className="eyebrow mb-2">Foto bukti (wajib)</p><PhotoCapture testId="wastage-photo" value={wf.photo} onChange={(p) => setWf({ ...wf, photo: p })} /></div>
              <button data-testid="wastage-submit" onClick={submitWastage} disabled={!wf.menu_id || !wf.qty || !wf.photo} className="btn-primary w-full">Catat & Kirim WhatsApp</button>
            </div>
          </Bento>
        </div>
      )}

      {tab === "history" && (
        <Bento testId="inventory-history">
          <table className="table-x"><thead><tr><th>{t("date")}</th><th>{t("material")}</th><th>{t("type")}</th><th>{t("qty")}</th><th className="hide-sm">After</th><th className="hide-xs">Cost</th><th className="hide-sm">Item</th><th className="hide-sm">{t("note")}</th><th className="hide-sm">By</th></tr></thead>
            <tbody>{tx.map((x) => <tr key={x.id}><td className="num text-xs">{x.date} {x.time || ""}</td><td>{x.material_name}</td><td><span className={`text-xs font-bold uppercase ${x.type === "in" ? "text-emerald-500" : x.type === "out" ? "text-red-500" : "text-amber-500"}`}>{x.type}</span></td>
              <td className="num">{x.qty} {x.unit}</td><td className="num hide-sm">{Math.round(x.after)}</td><td className="num hide-xs">{x.cost ? fmtRp(x.cost) : "-"}</td><td className="text-xs hide-sm">{x.item_name}{x.supplier ? ` · ${x.supplier}` : ""}</td><td className="text-muted-foreground text-xs hide-sm">{x.note}</td><td className="text-xs hide-sm">{x.user}</td></tr>)}</tbody></table>
        </Bento>
      )}

      <Dialog open={!!newMat} onOpenChange={(o) => !o && setNewMat(null)}>
        <DialogContent data-testid="new-material-dialog"><DialogHeader><DialogTitle>New Raw Material</DialogTitle></DialogHeader>
          {newMat && <form onSubmit={saveMat} className="space-y-3">
            <Field label="Name"><input data-testid="mat-name-input" className="field" value={newMat.name} onChange={(e) => setNewMat({ ...newMat, name: e.target.value })} required /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Unit"><Select value={newMat.unit} onChange={(v) => setNewMat({ ...newMat, unit: v })} options={["g", "ml", "pcs"]} /></Field>
              <Field label="Category"><Select value={newMat.category} onChange={(v) => setNewMat({ ...newMat, category: v })} options={["raw", "packaging"]} /></Field>
              <Field label="Qty per pack"><input data-testid="mat-packqty-input" type="number" className="field" value={newMat.pack_qty} onChange={(e) => setNewMat({ ...newMat, pack_qty: e.target.value })} required /></Field>
              <Field label="Pack price (Rp)"><input data-testid="mat-price-input" type="number" className="field" value={newMat.pack_price} onChange={(e) => setNewMat({ ...newMat, pack_price: e.target.value })} required /></Field>
              <Field label="Pack label"><input className="field" value={newMat.pack_label} onChange={(e) => setNewMat({ ...newMat, pack_label: e.target.value })} /></Field>
            </div>
            <button data-testid="mat-save-button" className="btn-primary w-full">{t("save")}</button></form>}
        </DialogContent>
      </Dialog>
    </div>
  );
}
