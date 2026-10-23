import { useEffect, useMemo, useState } from "react";
import { CheckCircle, LoaderCircle, ShoppingBag, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { Bento, Empty, Field, PageHeader, PhotoCapture, Select } from "../components/common";
import { today } from "../lib/helpers";

export default function Purchase() {
  const [orders, setOrders] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(today());
  const [note, setNote] = useState("");
  const [proof, setProof] = useState("");
  const [purchaseItems, setPurchaseItems] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const load = () => api.get("/purchase-orders").then((response) => setOrders(response.data));
  useEffect(() => { load(); }, []);
  const purchasable = useMemo(() => orders.filter((order) => !["arrived", "rejected", "purchased"].includes(order.status)), [orders]);
  const selected = useMemo(() => purchasable.find((order) => order.id === selectedId), [purchasable, selectedId]);
  useEffect(() => { setPurchaseItems(selected?.items || []); }, [selected]);
  const extractDraft = async () => {
    if (!proof) return toast.error("Upload bukti pembelian terlebih dahulu.");
    setExtracting(true);
    try {
      const { data } = await api.post("/expenses/extract", { proof });
      setVendorName(data.merchant || vendorName);
      setPurchaseDate(data.date || purchaseDate);
      setNote(data.note || note);
      toast.success(`Draft ${data.model?.includes("flash") ? "Gemini Flash" : "Gemini Pro"} siap direvisi.`);
    } catch (error) { toast.error(errMsg(error)); } finally { setExtracting(false); }
  };
  const save = async (event) => {
    event.preventDefault();
    if (!selectedId) return;
    setSaving(true);
    try {
      await api.post(`/purchase-orders/${selectedId}/purchase`, { vendor_name: vendorName, purchase_date: purchaseDate, note, proof, items: purchaseItems });
      toast.success("Pembelian dicatat. PO menjadi Sudah Dibeli.");
      setSelectedId(""); setVendorName(""); setNote(""); load();
    } catch (error) { toast.error(errMsg(error)); } finally { setSaving(false); }
  };
  return <div data-testid="purchase-page"><PageHeader><div className="mr-auto"><p className="eyebrow">Inventaris Production</p><h1 className="font-heading text-2xl font-bold">Purchase</h1></div></PageHeader><div className="grid gap-6 lg:grid-cols-[380px_1fr]"><Bento gold><form onSubmit={save} className="space-y-4"><div className="flex items-center gap-2"><ShoppingBag className="h-5 w-5 text-primary" /><p className="font-heading font-bold">Pembelian Aktual</p></div><PhotoCapture value={proof} onChange={setProof} label="Upload struk / bukti pembelian" testId="purchase-proof-capture" capture={false} fit="contain" /><button type="button" data-testid="purchase-ai-draft-button" onClick={extractDraft} disabled={!proof || extracting} className="btn-ghost w-full">{extracting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-primary" />}{extracting ? "Membaca struk..." : "Buat Draft dengan AI"}</button><Field label="Purchase Order"><Select testId="purchase-po-select" value={selectedId} onChange={setSelectedId} placeholder="Pilih PO" options={purchasable.map((order) => ({ value: order.id, label: `${order.po_number} · ${order.status}` }))} /></Field><Field label="Vendor / supplier"><input data-testid="purchase-vendor-input" className="field" value={vendorName} onChange={(event) => setVendorName(event.target.value)} /></Field><Field label="Tanggal pembelian"><input data-testid="purchase-date-input" type="date" className="field" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} /></Field><Field label="Catatan"><textarea data-testid="purchase-note-input" className="field min-h-20" value={note} onChange={(event) => setNote(event.target.value)} /></Field><button data-testid="purchase-save-button" disabled={!selectedId || saving} className="btn-primary w-full"><CheckCircle className="h-4 w-4" />Simpan Pembelian</button></form></Bento><Bento>{selected ? <div><p className="eyebrow">Rincian aktual — revisi sebelum simpan</p>{purchaseItems.map((item, index) => <div key={item.material_id} className="grid grid-cols-[1fr_90px_110px] gap-2 border-b py-3 text-sm"><span>{item.material_name}<small className="block text-muted-foreground">{item.unit}</small></span><input data-testid={`purchase-qty-${index}`} type="number" className="field" value={item.qty} onChange={(event) => setPurchaseItems((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, qty: Number(event.target.value) } : row))} /><input data-testid={`purchase-price-${index}`} type="number" className="field" value={item.unit_price} onChange={(event) => setPurchaseItems((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, unit_price: Number(event.target.value) } : row))} /></div>)}</div> : <Empty text="Pilih PO untuk mencatat pembelian." />}</Bento></div></div>;
}