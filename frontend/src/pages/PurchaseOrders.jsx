import { useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Bento, Empty, Field, PageHeader, Select } from "../components/common";

export default function PurchaseOrders() {
  const { user } = useAuth();
  const [materials, setMaterials] = useState([]);
  const [orders, setOrders] = useState([]);
  const [form, setForm] = useState({ material_id: "", qty: "", note: "" });
  const [decisionNote, setDecisionNote] = useState({});
  const canDecide = ["owner", "admin"].includes(user.role);
  const load = async () => {
    try {
      const [materialResponse, orderResponse] = await Promise.all([
        api.get("/materials"),
        api.get("/purchase-orders"),
      ]);
      setMaterials(materialResponse.data);
      setOrders(orderResponse.data);
    } catch (error) {
      toast.error(errMsg(error));
    }
  };
  useEffect(() => { load(); }, []);
  const submit = async (event) => {
    event.preventDefault();
    try {
      await api.post("/purchase-orders", { ...form, qty: Number(form.qty) });
      toast.success("Purchase Order dikirim untuk persetujuan.");
      setForm({ material_id: "", qty: "", note: "" });
      load();
    } catch (error) {
      toast.error(errMsg(error));
    }
  };
  const decide = async (order, decision) => {
    try {
      await api.post(`/purchase-orders/${order.id}/${decision}`, {
        note: decisionNote[order.id] || "",
      });
      toast.success(decision === "approve" ? "PO disetujui." : "PO ditolak.");
      load();
    } catch (error) {
      toast.error(errMsg(error));
    }
  };
  return (
    <div data-testid="purchase-orders-page">
      <PageHeader>
        <p className="eyebrow mr-auto">Production</p>
      </PageHeader>
      <div className="grid lg:grid-cols-[340px_1fr] gap-6">
        <Bento gold testId="purchase-order-form">
          <p className="font-heading font-bold text-xl">Purchase Order</p>
          <p className="text-xs text-muted-foreground mt-1">Ajukan kebutuhan bahan ke Owner/Admin.</p>
          <form onSubmit={submit} className="space-y-3 mt-5">
            <Field label="Bahan">
              <Select
                testId="purchase-order-material-select"
                value={form.material_id}
                onChange={(material_id) => setForm({ ...form, material_id })}
                placeholder="Pilih bahan"
                options={materials.map((material) => ({
                  value: material.id,
                  label: `${material.name} · stok ${material.stock} ${material.unit}`,
                }))}
              />
            </Field>
            <Field label="Jumlah">
              <input
                data-testid="purchase-order-qty-input"
                type="number"
                min="0.01"
                step="any"
                className="field num"
                value={form.qty}
                onChange={(event) => setForm({ ...form, qty: event.target.value })}
                required
              />
            </Field>
            <Field label="Catatan">
              <textarea
                data-testid="purchase-order-note-input"
                className="field min-h-24"
                value={form.note}
                onChange={(event) => setForm({ ...form, note: event.target.value })}
                placeholder="Contoh: kebutuhan untuk produksi akhir pekan"
              />
            </Field>
            <button data-testid="purchase-order-submit" className="btn-primary w-full" disabled={!form.material_id}>
              Kirim PO
            </button>
          </form>
        </Bento>
        <div className="space-y-3">
          <p className="eyebrow">Riwayat Purchase Order</p>
          {orders.map((order) => (
            <Bento key={order.id} testId={`purchase-order-${order.id}`}>
              <div className="flex flex-wrap justify-between gap-3">
                <div>
                  <p className="font-heading font-bold">{order.material_name}</p>
                  <p className="text-sm text-muted-foreground num">{order.qty} {order.unit} · {order.requested_by_name}</p>
                  {order.note && <p className="text-xs mt-2">{order.note}</p>}
                </div>
                <span data-testid={`purchase-order-status-${order.id}`} className={`h-fit px-2 py-1 rounded text-xs font-bold uppercase ${order.status === "approved" ? "bg-emerald-500/15 text-emerald-600" : order.status === "rejected" ? "bg-red-500/15 text-red-600" : "bg-amber-500/15 text-amber-600"}`}>{order.status === "approved" ? "disetujui" : order.status === "rejected" ? "ditolak" : "menunggu"}</span>
              </div>
              {canDecide && order.status === "pending" && (
                <div className="mt-4 space-y-2">
                  <input
                    data-testid={`purchase-order-decision-note-${order.id}`}
                    className="field text-xs"
                    placeholder="Catatan keputusan (opsional)"
                    value={decisionNote[order.id] || ""}
                    onChange={(event) => setDecisionNote({
                      ...decisionNote,
                      [order.id]: event.target.value,
                    })}
                  />
                  <div className="flex gap-2">
                    <button data-testid={`purchase-order-approve-${order.id}`} onClick={() => decide(order, "approve")} className="btn-primary text-xs"><Check className="w-4 h-4" />Setujui</button>
                    <button data-testid={`purchase-order-reject-${order.id}`} onClick={() => decide(order, "reject")} className="btn-ghost text-xs"><X className="w-4 h-4" />Tolak</button>
                  </div>
                </div>
              )}
              {order.approved_by && <p className="text-xs text-muted-foreground mt-3">Diputuskan oleh {order.approved_by}</p>}
              {order.decision_note && <p data-testid={`purchase-order-decision-${order.id}`} className="text-xs mt-2 border-l-2 border-primary pl-2">{order.decision_note}</p>}
            </Bento>
          ))}
          {!orders.length && <Empty text="Belum ada Purchase Order." />}
        </div>
      </div>
    </div>
  );
}