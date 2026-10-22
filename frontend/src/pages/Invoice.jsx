import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { fmtRp, today, fmtDate, waNumber } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { PageHeader, Bento, Field, Select, ReceiptModal, RLine, Empty } from "../components/common";

const Badge = ({ s }) => <span data-testid="invoice-status" className={`text-[10px] font-black tracking-wider px-2 py-0.5 rounded-full ${s === "paid" ? "bg-emerald-500 text-white" : "bg-red-500 text-white"}`}>{s === "paid" ? "PAID" : "UNPAID"}</span>;

export default function Invoice() {
  const { t, lang } = useT();
  const [menus, setMenus] = useState([]);
  const [f, setF] = useState({ customer_name: "", customer_phone: "", date: today(), payment_method: "cash", discount: 0, down_payment: 0, note: "" });
  const [qty, setQty] = useState({});
  const [result, setResult] = useState(null);
  const [list, setList] = useState([]);
  const [unpaid, setUnpaid] = useState(null);
  const [payAmt, setPayAmt] = useState("");
  const [busy, setBusy] = useState(false);
  const [clientId, setClientId] = useState(crypto.randomUUID());
  const load = () => api.get("/invoices").then((r) => setList(r.data));
  useEffect(() => { api.get("/menus").then((r) => setMenus(r.data)); load(); }, []);
  useEffect(() => {
    const p = f.customer_phone.replace(/\D/g, "");
    if (p.length >= 5) api.get("/customers/lookup", { params: { phone: p } }).then((r) => { setUnpaid(r.data.unpaid_invoice); const c = r.data.customers[0]; if (c?.name && !f.customer_name) setF((x) => ({ ...x, customer_name: c.name })); });
    else setUnpaid(null);
  }, [f.customer_phone]); // eslint-disable-line

  const subtotal = useMemo(() => menus.reduce((s, m) => s + (qty[m.id] || 0) * m.price, 0), [qty, menus]);
  const total = subtotal - Number(f.discount || 0);
  const remaining = Math.max(0, total - Number(f.down_payment || 0));
  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/invoices", { ...f, discount: Number(f.discount || 0), down_payment: Number(f.down_payment || 0), client_id: clientId, rows: menus.filter((m) => qty[m.id]).map((m) => ({ menu_id: m.id, qty: qty[m.id] })) });
      setResult(data); toast.success(data.invoice_no); setClientId(crypto.randomUUID()); load();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const pay = async () => {
    try { const { data } = await api.post(`/invoices/${result.id}/pay`, { amount: Number(payAmt), method: result.payment_method }); setResult(data); setPayAmt(""); toast.success(t("paid")); load(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const L = lang === "id";
  const waText = result && `*SI FOUR AM — INVOICE ${result.invoice_no}* [${result.status === "paid" ? t("paid") : t("unpaid")}]\n📅 ${fmtDate(result.date)} ${result.time || ""}\n👤 ${result.customer_name}\n----------------------------------\n` +
    result.rows.map((r) => `${r.name} x${r.qty} = ${fmtRp(r.subtotal)}`).join("\n") + `\n----------------------------------\nSubtotal: ${fmtRp(result.subtotal)}\n${L ? "Diskon" : "Discount"}: ${fmtRp(result.discount)}\n💰 *TOTAL: ${fmtRp(result.total)}*\n${t("downPayment")}: ${fmtRp(result.paid || 0)}\n❗ *${t("remainingPayment").toUpperCase()}: ${fmtRp(result.remaining || 0)}*\n\n${t("thankYou")} ☕`;

  return (
    <div data-testid="invoice-page">
      <PageHeader eyebrow="Superadmin" title={t("invoice")} />
      <div className="grid lg:grid-cols-3 gap-6">
        <Bento gold className="lg:col-span-2 fade-up" testId="invoice-form">
          <div className="grid grid-cols-2 gap-3 mb-3 invoice-detail-fields">
            <Field label={`${t("customer")} WhatsApp`}>
              <input
                data-testid="invoice-phone-input"
                className="field h-5 px-2 text-xs"
                placeholder="08xx"
                value={f.customer_phone}
                onChange={(event) => setF({ ...f, customer_phone: event.target.value })}
              />
            </Field>
            <Field label={t("customer")}>
              <input
                data-testid="invoice-customer-input"
                className="field h-5 px-2 text-xs"
                value={f.customer_name}
                onChange={(event) => setF({ ...f, customer_name: event.target.value })}
              />
            </Field>
            <Field label={t("date")}>
              <input
                data-testid="invoice-date-input"
                type="date"
                className="field h-5 px-2 text-xs"
                value={f.date}
                onChange={(event) => setF({ ...f, date: event.target.value })}
              />
            </Field>
            <Field label={t("method")}>
              <Select
                testId="invoice-payment-select"
                value={f.payment_method}
                onChange={(value) => setF({ ...f, payment_method: value })}
                className="h-5 px-2 text-xs"
                options={[
                  { value: "cash", label: "Cash" },
                  { value: "qris", label: "QRIS / Transfer" },
                ]}
              />
            </Field>
          </div>
          {unpaid && <button data-testid="unpaid-hint" onClick={() => setResult(unpaid)} className="w-full text-left rounded-xl bg-red-500/10 border border-red-500/30 p-3 text-xs mb-4 flex justify-between items-center"><span>⚠️ {unpaid.invoice_no} · {unpaid.customer_name} · {t("remainingPayment")} <b className="num">{fmtRp(unpaid.remaining)}</b></span><Badge s="unpaid" /></button>}
          <div className="overflow-x-auto -mx-5 px-5">
            <table className="table-x invoice-table">
              <thead>
                <tr>
                  <th>{t("menu")}</th>
                  <th>{t("price")}</th>
                  <th>{t("qty")}</th>
                  <th className="text-right">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {menus.map((menu) => (
                  <tr key={menu.id}>
                    <td className="max-w-[9rem] truncate whitespace-nowrap text-xs font-semibold">
                      {menu.name}
                    </td>
                    <td className="num whitespace-nowrap text-[10px] text-muted-foreground">
                      {fmtRp(menu.price)}
                    </td>
                    <td className="text-center">
                      <input
                        data-testid={`invoice-qty-${menu.id}`}
                        type="number"
                        min="0"
                        className="field h-8 w-8 rounded-full p-0 text-center text-xs num"
                        value={qty[menu.id] || ""}
                        placeholder="0"
                        onChange={(event) => {
                          setQty({ ...qty, [menu.id]: Number(event.target.value) });
                        }}
                      />
                    </td>
                    <td className="num whitespace-nowrap text-right text-xs">
                      {fmtRp((qty[menu.id] || 0) * menu.price)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="grid sm:grid-cols-3 gap-3 mt-4">
            <Field label={`${L ? "Diskon" : "Discount"} (Rp)`}><input data-testid="invoice-discount-input" type="number" className="field num" value={f.discount} onChange={(e) => setF({ ...f, discount: e.target.value })} /></Field>
            <Field label={`${t("downPayment")} (Rp)`}><input data-testid="invoice-dp-input" type="number" className="field num" value={f.down_payment} onChange={(e) => setF({ ...f, down_payment: e.target.value })} /></Field>
            <Field label={t("note")}><input data-testid="invoice-note-input" className="field" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></Field>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mt-6 pt-6 border-t border-border/60">
            <div><p className="text-xs text-muted-foreground">Subtotal {fmtRp(subtotal)} · Total {fmtRp(total)} · DP {fmtRp(f.down_payment)}</p><p className="eyebrow mt-2">{t("remainingPayment")}</p><p data-testid="invoice-remaining" className="text-3xl font-black num font-heading text-primary">{fmtRp(remaining)}</p></div>
            <button data-testid="invoice-save-button" onClick={save} disabled={!f.customer_name || subtotal <= 0 || busy} className="btn-primary h-12 px-8">{t("createInvoice")}</button>
          </div>
        </Bento>
        <Bento className="fade-up" testId="invoice-list">
          <p className="eyebrow mb-3">{t("history")}</p>
          {list.map((i) => <div key={i.id} data-testid={`invoice-item-${i.id}`} onClick={() => setResult(i)} className="py-2 border-b border-border/50 text-sm cursor-pointer hover:bg-muted/40 rounded-lg px-1"><div className="flex justify-between items-center"><span className="font-semibold">{i.customer_name}</span><Badge s={i.status || "paid"} /></div><div className="flex justify-between text-xs text-muted-foreground num"><span>{i.invoice_no} · {i.date}</span><span className="font-bold text-foreground">{fmtRp(i.total)}</span></div></div>)}
          {!list.length && <Empty text={t("noData")} />}
        </Bento>
      </div>
      <ReceiptModal open={!!result} onClose={() => { setResult(null); setQty({}); }} title={`Invoice ${result?.invoice_no || ""}`} waText={waText} waPhone={result?.customer_phone} filename={`${result?.invoice_no}.png`} testId="invoice-receipt">
        {result && <>
          <div className="flex justify-center mb-2"><Badge s={result.status || "paid"} /></div>
          <RLine l="Invoice No" r={result.invoice_no} /><RLine l={t("date")} r={`${fmtDate(result.date)} ${result.time || ""}`} /><RLine l="Bill to" r={result.customer_name} /><RLine l="WhatsApp" r={result.customer_phone ? `+${waNumber(result.customer_phone)}` : "-"} />
          <div className="border-t border-dashed border-gray-300 my-2" />
          {result.rows.map((r) => <RLine key={r.menu_id} l={`${r.name} ×${r.qty} @ ${fmtRp(r.price)}`} r={fmtRp(r.subtotal)} />)}
          <div className="border-t border-dashed border-gray-300 my-2" />
          <RLine l="Subtotal" r={fmtRp(result.subtotal)} /><RLine l={L ? "Diskon" : "Discount"} r={fmtRp(result.discount)} /><RLine bold l="TOTAL" r={fmtRp(result.total)} /><RLine l={t("downPayment")} r={fmtRp(result.paid ?? result.down_payment ?? 0)} />
          <div className="flex justify-between items-center pt-2 mt-1 border-t border-gray-300"><span className="text-xs font-black uppercase">{t("remainingPayment")}</span><span data-testid="receipt-remaining" className="num text-lg font-black">{fmtRp(result.remaining ?? 0)}</span></div>
          {result.status === "unpaid" && <div className="flex gap-2 mt-3" data-testid="invoice-pay-row"><input data-testid="invoice-pay-input" type="number" className="field h-9 num text-black bg-white border-gray-300" placeholder="Rp" value={payAmt} onChange={(e) => setPayAmt(e.target.value)} /><button data-testid="invoice-pay-button" onClick={pay} disabled={!payAmt} className="btn-primary h-9 px-4 text-xs">{L ? "Bayar" : "Pay"}</button></div>}
          <p className="text-[10px] text-gray-400 text-center mt-3">Issued by {result.created_by} · SI FOUR AM</p>
        </>}
      </ReceiptModal>
    </div>
  );
}
