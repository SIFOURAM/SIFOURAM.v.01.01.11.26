import { useEffect, useState } from "react";
import { CheckCircle, ShoppingBag } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { Bento, Empty, Field, PageHeader, Select } from "../components/common";
import { today } from "../lib/helpers";

export default function Purchase() {
  const [orders, setOrders] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(today());
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const load = () => api.get("/purchase-orders").then((response) => setOrders(response.data));
  useEffect(() => { load(); }, []);
  const approved = orders.filter((order) => order.status === "approved");
  const selected = approved.find((order) => order.id === selectedId);
  const save = async (event) => {
    event.preventDefault();
    if (!selectedId) return;
    setSaving(true);
    try {
      await api.post(`/purchase-orders/${selectedId}/purchase`, { vendor_name: vendorName, purchase_date: purchaseDate, note });
      toast.success("Pembelian dicatat. PO menjadi Sudah Dibeli.");
      setSelectedId(""); setVendorName(""); setNote(""); load();
    } catch (error) { toast.error(errMsg(error)); } finally { setSaving(false); }
  };
  return <div data-testid="purchase-page"><PageHeader><div className="mr-auto"><p className="eyebrow">Inventaris Production</p><h1 className="font-heading text-2xl font-bold">Purchase</h1></div></PageHeader><div className="grid gap-6 lg:grid-cols-[380px_1fr]"><Bento gold><form onSubmit={save} className="space-y-4"><div className="flex items-center gap-2"><ShoppingBag className="h-5 w-5 text-primary" /><p className="font-heading font-bold">Pembelian Aktual</p></div><Field label="PO Disetujui"><Select testId="purchase-po-select" value={selectedId} onChange={setSelectedId} placeholder="Pilih PO" options={approved.map((order) => ({ value: order.id, label: order.po_number }))} /></Field><Field label="Vendor / supplier"><input data-testid="purchase-vendor-input" className="field" value={vendorName} onChange={(event) => setVendorName(event.target.value)} /></Field><Field label="Tanggal pembelian"><input data-testid="purchase-date-input" type="date" className="field" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} /></Field><Field label="Catatan"><textarea data-testid="purchase-note-input" className="field min-h-20" value={note} onChange={(event) => setNote(event.target.value)} /></Field><button data-testid="purchase-save-button" disabled={!selectedId || saving} className="btn-primary w-full"><CheckCircle className="h-4 w-4" />Simpan Pembelian</button></form></Bento><Bento>{selected ? <div><p className="eyebrow">Rincian PO</p>{(selected.items || []).map((item) => <div key={item.material_id} className="flex justify-between border-b py-3 text-sm"><span>{item.material_name}</span><span className="num">{item.qty} {item.unit}</span></div>)}</div> : <Empty text="Pilih PO Disetujui untuk mencatat pembelian." />}</Bento></div></div>;
}