import { useState } from "react";
import { FileScan, LoaderCircle, Save, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { today } from "../lib/helpers";
import { Field, PhotoCapture, Select } from "./common";

export const EXPENSE_CATEGORIES = [
  "Raw Material",
  "Packaging",
  "Fuel / Transport",
  "Salary",
  "Rent",
  "Utilities",
  "Marketing",
  "Equipment",
  "Other",
];

const emptyExpense = () => ({
  date: today(),
  category: "Raw Material",
  amount: "",
  note: "",
  account: "cash",
  type: "expense",
});

export default function ExpenseEntryPanel({ onSaved }) {
  const [form, setForm] = useState(emptyExpense);
  const [proof, setProof] = useState("");
  const [extraction, setExtraction] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const extract = async () => {
    if (!proof) {
      toast.error("Tambahkan foto struk atau bukti pembayaran terlebih dahulu.");
      return;
    }
    setExtracting(true);
    try {
      const response = await api.post("/expenses/extract", { proof });
      const draft = response.data;
      setForm((current) => ({
        ...current,
        date: draft.date || current.date,
        category: EXPENSE_CATEGORIES.includes(draft.category) ? draft.category : current.category,
        amount: draft.amount ? String(draft.amount) : current.amount,
        note: draft.note || current.note,
        account: draft.account === "bank" ? "bank" : "cash",
      }));
      setExtraction(draft);
      toast.success("Draft dari struk siap ditinjau.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setExtracting(false);
    }
  };

  const save = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await api.post("/expenses", {
        ...form,
        amount: Number(form.amount),
        proof: proof || null,
        extraction,
      });
      toast.success("Pengeluaran berhasil dicatat.");
      setForm(emptyExpense());
      setProof("");
      setExtraction(null);
      onSaved();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="space-y-4" data-testid="expense-entry-panel">
      <div className="flex items-start gap-3">
        <div
          className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/15"
        >
          <FileScan className="h-4 w-4 text-primary" />
        </div>
        <div>
          <p className="font-heading text-lg font-bold">Pembelian & Pengeluaran</p>
          <p className="text-xs text-muted-foreground">
            Scan struk untuk membuat draft, lalu periksa sebelum menyimpan.
          </p>
        </div>
      </div>

      <PhotoCapture
        value={proof}
        onChange={(value) => {
          setProof(value);
          setExtraction(null);
        }}
        label="Foto struk atau bukti pembayaran"
        testId="expense-proof-capture"
        capture={false}
      />

      <button
        type="button"
        data-testid="expense-ai-extract-button"
        onClick={extract}
        disabled={!proof || extracting}
        className="btn-ghost w-full disabled:cursor-not-allowed"
      >
        {extracting ? (
          <LoaderCircle className="h-4 w-4 animate-spin" />
        ) : (
          <Sparkles className="h-4 w-4 text-primary" />
        )}
        {extracting ? "Membaca bukti..." : "Baca dengan AI"}
      </button>

      {extraction && (
        <div
          data-testid="expense-ai-draft-status"
          className="border-l-2 border-primary bg-primary/5 px-3 py-2 text-xs"
        >
          Draft AI siap ditinjau{extraction.merchant ? ` · ${extraction.merchant}` : ""}.
          {extraction.items?.length ? ` ${extraction.items.join(", ")}` : ""}
        </div>
      )}

      <form onSubmit={save} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Tanggal">
            <input
              data-testid="expense-date-input"
              type="date"
              className="field"
              value={form.date}
              onChange={(event) => update("date", event.target.value)}
              required
            />
          </Field>
          <Field label="Akun pembayaran">
            <Select
              testId="expense-account-select"
              value={form.account}
              onChange={(value) => update("account", value)}
              options={[
                { value: "cash", label: "Cash" },
                { value: "bank", label: "Bank / QRIS" },
              ]}
            />
          </Field>
        </div>
        <Field label="Kategori">
          <Select
            testId="expense-category-select"
            value={form.category}
            onChange={(value) => update("category", value)}
            options={EXPENSE_CATEGORIES}
          />
        </Field>
        <Field label="Nominal">
          <input
            data-testid="expense-amount-input"
            type="number"
            min="1"
            step="1"
            className="field num"
            value={form.amount}
            onChange={(event) => update("amount", event.target.value)}
            required
          />
        </Field>
        <Field label="Catatan / merchant">
          <textarea
            data-testid="expense-note-input"
            className="field min-h-20 py-2"
            value={form.note}
            onChange={(event) => update("note", event.target.value)}
            placeholder="Contoh: pembelian susu untuk produksi"
          />
        </Field>
        <button
          data-testid="expense-save-button"
          disabled={saving}
          className="btn-primary w-full"
        >
          {saving ? (
            <LoaderCircle className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {saving ? "Menyimpan..." : "Simpan Pengeluaran"}
        </button>
      </form>
    </section>
  );
}