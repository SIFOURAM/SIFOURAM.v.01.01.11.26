import { useEffect, useState } from "react";
import { Minus, Plus, Send } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { Field, Select } from "./common";

const emptyItem = () => ({ material_id: "", qty: "", unit_price: "" });

export default function PurchaseOrderForm({ materials, initialMaterialIds, onCreated }) {
  const [items, setItems] = useState([emptyItem()]);
  const [vendorName, setVendorName] = useState("");
  const [expectedDate, setExpectedDate] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!initialMaterialIds.length) {
      return;
    }
    setItems(initialMaterialIds.map((materialId) => ({
      material_id: materialId,
      qty: "",
      unit_price: "",
    })));
  }, [initialMaterialIds]);

  const updateItem = (index, key, value) => {
    setItems((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, [key]: value } : item
    )));
  };

  const submit = async (event) => {
    event.preventDefault();
    const requestItems = items
      .filter((item) => item.material_id && Number(item.qty) > 0)
      .map((item) => ({
        material_id: item.material_id,
        qty: Number(item.qty),
        unit_price: Number(item.unit_price || 0),
      }));
    if (!requestItems.length) {
      toast.error("Tambahkan minimal satu bahan dengan jumlah yang valid.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/purchase-orders", {
        items: requestItems,
        vendor_name: vendorName,
        expected_date: expectedDate || null,
        note,
      });
      toast.success("PO dikirim untuk review Admin.");
      setItems([emptyItem()]);
      setVendorName("");
      setExpectedDate("");
      setNote("");
      onCreated();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4" data-testid="purchase-order-form">
      <div>
        <p className="font-heading text-lg font-bold">Purchase Order</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Tambahkan bahan, lalu kirim untuk review Admin dan persetujuan Owner.
        </p>
      </div>

      <div className="space-y-3">
        {items.map((item, index) => (
          <div
            key={`${item.material_id}-${index}`}
            data-testid={`purchase-order-item-${index}`}
            className="space-y-2 border-l-2 border-primary/40 pl-3"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="eyebrow">Bahan {index + 1}</p>
              {items.length > 1 && (
                <button
                  type="button"
                  data-testid={`purchase-order-remove-item-${index}`}
                  onClick={() => setItems((current) => (
                    current.filter((_, itemIndex) => itemIndex !== index)
                  ))}
                  className={[
                    "flex h-7 w-7 items-center justify-center rounded-md",
                    "text-muted-foreground hover:bg-muted",
                  ].join(" ")}
                  aria-label="Hapus bahan"
                >
                  <Minus className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <Select
              testId={`purchase-order-material-select-${index}`}
              value={item.material_id}
              onChange={(value) => updateItem(index, "material_id", value)}
              placeholder="Pilih bahan"
              options={materials.map((material) => ({
                value: material.id,
                label: `${material.name} · stok ${material.stock} ${material.unit}`,
              }))}
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                data-testid={`purchase-order-qty-input-${index}`}
                type="number"
                min="0.01"
                step="any"
                className="field num"
                value={item.qty}
                onChange={(event) => updateItem(index, "qty", event.target.value)}
                placeholder="Jumlah"
                required
              />
              <input
                data-testid={`purchase-order-price-input-${index}`}
                type="number"
                min="0"
                step="1"
                className="field num"
                value={item.unit_price}
                onChange={(event) => updateItem(index, "unit_price", event.target.value)}
                placeholder="Harga per unit"
              />
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        data-testid="purchase-order-add-item"
        onClick={() => setItems((current) => [...current, emptyItem()])}
        className="btn-ghost h-9 w-full px-3 text-xs"
      >
        <Plus className="h-3.5 w-3.5" /> Tambah bahan
      </button>

      <Field label="Vendor / supplier">
        <input
          data-testid="purchase-order-vendor-input"
          className="field"
          value={vendorName}
          onChange={(event) => setVendorName(event.target.value)}
          placeholder="Contoh: Toko Bahan Jaya"
        />
      </Field>
      <Field label="Target tiba">
        <input
          data-testid="purchase-order-expected-date-input"
          type="date"
          className="field"
          value={expectedDate}
          onChange={(event) => setExpectedDate(event.target.value)}
        />
      </Field>
      <Field label="Catatan">
        <textarea
          data-testid="purchase-order-note-input"
          className="field min-h-20 py-2"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Kebutuhan produksi akhir pekan"
        />
      </Field>
      <button
        data-testid="purchase-order-submit"
        disabled={saving}
        className="btn-primary w-full"
      >
        <Send className="h-4 w-4" />
        {saving ? "Mengirim..." : "Kirim PO untuk Review"}
      </button>
    </form>
  );
}