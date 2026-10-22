import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { fmtRp, today, compressImage } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Bento, Field, Select, Empty } from "../components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";

export default function MenuStock() {
  const { t } = useT();
  const { user } = useAuth();
  const [menus, setMenus] = useState([]);
  const [mats, setMats] = useState([]);
  const [tx, setTx] = useState([]);
  const [form, setForm] = useState({ menu_id: "", qty: "", type: "produce", date: today(), note: "" });
  const [edit, setEdit] = useState(null);

  const load = () => Promise.all([api.get("/menus"), api.get("/menu-stock/tx"), api.get("/materials")]).then(([a, b, c]) => { setMenus(a.data); setTx(b.data); setMats(c.data); });
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    try { await api.post("/menu-stock/produce", { ...form, qty: Number(form.qty) }); toast.success(form.type === "produce" ? "Production saved, raw materials deducted" : "Stock adjusted"); setForm({ ...form, qty: "" }); load(); }
    catch (err) { toast.error(errMsg(err)); }
  };
  const saveMenu = async (e) => {
    e.preventDefault();
    const body = { name: edit.name, price: Number(edit.price), max_stock: Number(edit.max_stock), photo: edit.photo, recipe: edit.recipe.filter((r) => r.material_id).map((r) => ({ material_id: r.material_id, qty: Number(r.qty) })) };
    try { edit.id ? await api.put(`/menus/${edit.id}`, body) : await api.post("/menus", body); toast.success("Menu saved"); setEdit(null); load(); }
    catch (err) { toast.error(errMsg(err)); }
  };

  return (
    <div data-testid="menu-stock-page">
      <PageHeader eyebrow="Bar Team" title={t("menuStock")} />
      <div className="grid lg:grid-cols-3 gap-6">
        <Bento gold className="fade-up" testId="produce-form">
          <p className="eyebrow mb-4">Input Stock (Production)</p>
          <form onSubmit={submit} className="space-y-3">
            <Field label="Menu"><Select testId="produce-menu-select" value={form.menu_id} onChange={(v) => setForm({ ...form, menu_id: v })} placeholder="Select menu" options={menus.map((m) => ({ value: m.id, label: m.name }))} /></Field>
            <Field label="Type"><Select testId="produce-type-select" value={form.type} onChange={(v) => setForm({ ...form, type: v })} options={[{ value: "produce", label: "Produce (deduct raw materials)" }, { value: "adjust", label: "Set actual stock (opname)" }]} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Cups"><input data-testid="produce-qty-input" type="number" className="field" value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} required /></Field>
              <Field label={t("date")}><input type="date" className="field" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></Field>
            </div>
            <button data-testid="produce-submit-button" className="btn-primary w-full" disabled={!form.menu_id}>{t("save")}</button>
          </form>
          {form.menu_id && form.type === "produce" && form.qty > 0 && (
            <div className="mt-4 text-xs text-muted-foreground"><p className="eyebrow mb-1">Will deduct</p>
              {menus.find((m) => m.id === form.menu_id)?.recipe.map((r, i) => <div key={i} className="flex justify-between"><span>{r.name}</span><span className="num">{r.qty * form.qty} {r.unit}</span></div>)}</div>)}
        </Bento>
        <div className="lg:col-span-2 grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
          <div className="sm:col-span-2 xl:col-span-3 flex items-center justify-between gap-3">
            <p className="eyebrow">Recipes</p>
            {user.role === "owner" && <button data-testid="add-menu-button" onClick={() => setEdit({ name: "", price: "", max_stock: 30, photo: "", recipe: [{ material_id: "", qty: "" }] })} className="btn-primary h-9 px-3 text-xs"><Plus className="w-4 h-4" />Add Menu</button>}
          </div>
          {menus.map((m) => (
            <Bento key={m.id} className="fade-up p-0 overflow-hidden" testId={`menu-card-${m.id}`}>
              <div className="h-28 bg-muted relative">{m.photo && <img src={m.photo} alt={m.name} className="w-full h-full object-cover" />}
                {user.role === "owner" && <button data-testid={`edit-menu-${m.id}`} onClick={() => setEdit({ ...m, recipe: m.recipe.length ? m.recipe : [{ material_id: "", qty: "" }] })} className="absolute top-2 right-2 w-8 h-8 rounded-full bg-black/60 text-white flex items-center justify-center"><Pencil className="w-3.5 h-3.5" /></button>}
                <span className="absolute bottom-2 left-3 text-[10px] font-bold uppercase text-white bg-primary rounded-full px-2 py-0.5">#{m.order}</span></div>
              <div className="p-4"><p className="font-heading font-bold text-sm">{m.name}</p><p className="text-xs text-muted-foreground">{fmtRp(m.price)} · HPP {fmtRp(m.cost)}</p>
                <div className="flex justify-between items-end mt-3"><span className="eyebrow">{t("remaining")}</span><span data-testid={`menu-stock-${m.id}`} className={`text-2xl font-bold num ${m.stock < 10 ? "text-red-500" : ""}`}>{m.stock}</span></div></div>
            </Bento>))}
        </div>
      </div>
      <Bento scrollable className="mt-6 overflow-x-auto" testId="menu-stock-history">
        <p className="eyebrow mb-4">Stock Movements</p>
        <table className="table-x"><thead><tr><th>Date</th><th>Menu</th><th>Type</th><th>Qty</th><th>After</th><th>By</th></tr></thead>
          <tbody>{tx.length ? tx.slice(0, 50).map((x) => <tr key={x.id}><td className="num">{x.date}</td><td>{x.menu_name}</td><td className="text-xs uppercase font-bold">{x.type}</td><td className="num">{x.qty}</td><td className="num">{x.after}</td><td className="text-xs">{x.user}</td></tr>) : <tr><td colSpan="6"><Empty text="Belum ada pergerakan stock." /></td></tr>}</tbody></table>
      </Bento>

      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto" data-testid="menu-dialog"><DialogHeader><DialogTitle>{edit?.id ? "Edit Menu" : "New Menu"}</DialogTitle></DialogHeader>
          {edit && <form onSubmit={saveMenu} className="space-y-3">
            <Field label="Name"><input data-testid="menu-name-input" className="field" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} required /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Selling price"><input data-testid="menu-price-input" type="number" className="field" value={edit.price} onChange={(e) => setEdit({ ...edit, price: e.target.value })} required /></Field>
              <Field label="Rider max stock"><input type="number" className="field" value={edit.max_stock} onChange={(e) => setEdit({ ...edit, max_stock: e.target.value })} /></Field>
            </div>
            <Field label="Photo (URL or upload)"><input data-testid="menu-photo-input" className="field mb-2" value={edit.photo || ""} onChange={(e) => setEdit({ ...edit, photo: e.target.value })} placeholder="https://..." />
              <input type="file" accept="image/*" className="text-xs" onChange={async (e) => { const f = e.target.files?.[0]; if (f) setEdit({ ...edit, photo: await compressImage(f, 600) }); }} /></Field>
            <p className="eyebrow">Recipe</p>
            {edit.recipe.map((r, i) => (
              <div key={i} className="flex gap-2"><Select className="flex-1" value={r.material_id} onChange={(v) => { const rc = [...edit.recipe]; rc[i] = { ...rc[i], material_id: v }; setEdit({ ...edit, recipe: rc }); }} placeholder="Material" options={mats.filter((m) => m.category === "raw").map((m) => ({ value: m.id, label: `${m.name} (${m.unit})` }))} />
                <input type="number" step="any" className="field w-24" placeholder="qty" value={r.qty} onChange={(e) => { const rc = [...edit.recipe]; rc[i] = { ...rc[i], qty: e.target.value }; setEdit({ ...edit, recipe: rc }); }} /></div>))}
            <button type="button" onClick={() => setEdit({ ...edit, recipe: [...edit.recipe, { material_id: "", qty: "" }] })} className="text-xs font-semibold text-primary">+ ingredient</button>
            <button data-testid="menu-save-button" className="btn-primary w-full">{t("save")}</button></form>}
        </DialogContent>
      </Dialog>
    </div>
  );
}
