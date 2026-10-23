import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import {
  ArrowDownRight,
  ArrowUpRight,
  Landmark,
  Wallet,
  Trash2,
  Image,
  FileDown,
  FileSpreadsheet,
  MessageCircle,
} from "lucide-react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";
import { api, errMsg } from "../lib/api";
import { fmtRp, today, openWA, nowTime } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { PageHeader, Bento, Stat, DateFilter, Empty } from "../components/common";
import ExpenseEntryPanel from "../components/ExpenseEntryPanel";

const COLORS = ["#FF6B00", "#F97316", "#EF4444", "#FB923C", "#FF7A1A", "#C2410C", "#EA580C", "#9A3412", "#9CA3AF"];

export default function Finance() {
  const { t } = useT();
  const [range, setRange] = useState(null);
  const [d, setD] = useState(null);
  const load = useCallback(() => {
    if (!range) return;
    api.get("/finance/summary", { params: range })
      .then((response) => setD(response.data))
      .catch((error) => toast.error(errMsg(error)));
  }, [range]);
  useEffect(() => { load(); }, [load]);
  const del = async (id) => { await api.delete(`/expenses/${id}`); load(); };
  const rows = () => d.ledger.map((l) => [l.date, l.type === "in" ? "IN" : "OUT", l.account.toUpperCase(), l.category, l.desc, l.item_name || "", l.material_name || "", l.amount, l.balance_cash, l.balance_bank]);
  const HEAD = ["Date", "Type", "Account", "Category", "Description", "Purchased item", "Raw material", "Amount", "Cash balance", "Bank balance"];
  const excel = () => {
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([["SI FOUR AM Financial Report", `${range.start} → ${range.end}`, `${today()} ${nowTime()}`], [], ["Income", d.income], ["Outgoing", d.outgo], ["Net", d.net], ["COGS", d.cogs], ["Gross profit", d.gross_profit], ["Cash balance", d.cash_balance], ["Bank balance", d.bank_balance], ["Inventory value", d.inventory_value]]), "Summary");
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([HEAD, ...rows()]), "Ledger");
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([["Category", "Amount"], ...d.by_category.map((c) => [c.name, c.amount])]), "By Category");
    XLSX.writeFile(wb, `SIFOURAM_Finance_${range.start}_${range.end}.xlsx`);
  };
  const pdf = () => {
    const doc = new jsPDF({ orientation: "landscape" });
    doc.setFontSize(15); doc.text("SI FOUR AM — Financial Report", 14, 14); doc.setFontSize(9); doc.text(`${range.start} → ${range.end} · ${today()} ${nowTime()} WIB`, 14, 20);
    autoTable(doc, { startY: 25, head: [["Income", "Outgoing", "Net", "COGS", "Gross profit", "Cash", "Bank"]], body: [[d.income, d.outgo, d.net, d.cogs, d.gross_profit, d.cash_balance, d.bank_balance].map((v) => fmtRp(v))], headStyles: { fillColor: [255, 107, 0] }, styles: { fontSize: 8 } });
    autoTable(doc, { head: [HEAD], body: rows().map((r) => r.map((v, i) => (i >= 7 ? Number(v).toLocaleString("id-ID") : v))), styles: { fontSize: 7, cellPadding: 1.5 }, headStyles: { fillColor: [212, 175, 55] }, theme: "grid" });
    doc.save(`SIFOURAM_Finance_${range.start}_${range.end}.pdf`);
  };
  const wa = () => openWA(`*SI FOUR AM — ${t("finance").toUpperCase()}*\n📅 ${range.start} → ${range.end}\n----------------------------------\n📈 ${t("income")}: ${fmtRp(d.income)}\n📉 ${t("outgo")}: ${fmtRp(d.outgo)}\n💰 Net: ${fmtRp(d.net)}\n🧾 COGS: ${fmtRp(d.cogs)}\n📊 Gross profit: ${fmtRp(d.gross_profit)}\n💵 Cash: ${fmtRp(d.cash_balance)}\n🏦 Bank: ${fmtRp(d.bank_balance)}\n📦 Inventory: ${fmtRp(d.inventory_value)}\n----------------------------------\n${d.by_category.map((c) => `• ${c.name}: ${fmtRp(c.amount)}`).join("\n")}`);

  return (
    <div data-testid="finance-page">
      <PageHeader eyebrow="Dashboard · Laporan" title="Laporan Keuangan">
        {d && <div className="flex gap-2"><button data-testid="fin-excel-button" onClick={excel} className="btn-ghost h-9 px-3 text-xs"><FileSpreadsheet className="w-3.5 h-3.5" />{t("excel")}</button><button data-testid="fin-pdf-button" onClick={pdf} className="btn-ghost h-9 px-3 text-xs"><FileDown className="w-3.5 h-3.5" />PDF</button><button data-testid="fin-wa-button" onClick={wa} className="btn-wa h-9 px-3 text-xs"><MessageCircle className="w-3.5 h-3.5" />WA</button></div>}
        <DateFilter onChange={setRange} />
      </PageHeader>
      {d && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          <Stat gold label={t("income")} value={fmtRp(d.income)} icon={ArrowUpRight} testId="fin-income" />
          <Stat label={t("outgo")} value={fmtRp(d.outgo)} icon={ArrowDownRight} testId="fin-outgo" />
          <Stat label="Cash balance" value={fmtRp(d.cash_balance)} sub={`Handed over: ${fmtRp(d.handover_total)}`} icon={Wallet} testId="fin-cash" />
          <Stat label="Bank / QRIS balance" value={fmtRp(d.bank_balance)} icon={Landmark} testId="fin-bank" />
          <Stat label="Net profit" value={fmtRp(d.net)} sub="income − all outgoing" testId="fin-net" className={d.net >= 0 ? "" : "border-red-500/40"} />
          <Stat label="Gross profit (after HPP)" value={fmtRp(d.gross_profit)} sub={`COGS ${fmtRp(d.cogs)}`} testId="fin-gross" />
          <Stat label="Inventory value" value={fmtRp(d.inventory_value)} sub="raw + packaging on hand" testId="fin-inventory" />
          <Stat label="Margin" value={d.income ? `${Math.round((d.net / d.income) * 100)}%` : "—"} sub="net / income" testId="fin-margin" />

          <Bento gold className="col-span-2 lg:col-span-1 fade-up" testId="expense-form">
            <ExpenseEntryPanel onSaved={load} />
          </Bento>
          <Bento className="col-span-2 lg:col-span-1 fade-up" testId="expense-breakdown">
            <p className="eyebrow mb-4">Outgoing by category</p>
            {d.by_category.length ? <><ResponsiveContainer width="100%" height={160}><PieChart><Pie data={d.by_category} dataKey="amount" nameKey="name" innerRadius={45} outerRadius={70} paddingAngle={3}>{d.by_category.map((entry, i) => <Cell key={entry.name} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip formatter={(v) => fmtRp(v)} contentStyle={{ borderRadius: 12, fontSize: 12 }} /></PieChart></ResponsiveContainer>
              <ul className="text-xs space-y-1">{d.by_category.map((c, i) => <li key={c.name} className="flex justify-between"><span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />{c.name}</span><b className="num">{fmtRp(c.amount)}</b></li>)}</ul></> : <Empty text={t("noData")} />}
          </Bento>
          <Bento className="col-span-2 fade-up max-h-[560px] overflow-y-auto" testId="ledger">
            <p className="eyebrow mb-4">Cash / bank ledger · running balance</p>
            <table className="table-x"><thead><tr><th>{t("date")}</th><th>{t("category")}</th><th className="hide-sm">Acct</th><th className="text-right">{t("amount")}</th><th className="text-right hide-sm">Cash</th><th className="text-right hide-sm">Bank</th><th /></tr></thead>
              <tbody>{d.ledger.map((l) => <tr key={l.id || `${l.date}-${l.category}-${l.amount}`}><td className="num text-xs">{l.date}</td><td><span className="font-semibold text-xs">{l.category}</span><span className="block text-[10px] text-muted-foreground">{l.desc}</span></td><td className="text-[10px] uppercase hide-sm">{l.account}</td>
                <td className={`num text-right font-semibold ${l.type === "in" ? "text-emerald-500" : "text-red-500"}`}>{l.type === "in" ? "+" : "−"}{fmtRp(l.amount)}</td><td className="num text-right text-xs hide-sm">{fmtRp(l.balance_cash)}</td><td className="num text-right text-xs hide-sm">{fmtRp(l.balance_bank)}</td>
                <td className="flex items-center justify-end gap-2">
                  {l.proof && (
                    <a
                      data-testid={`ledger-proof-${l.id}`}
                      href={l.proof}
                      target="_blank"
                      rel="noreferrer"
                      className="text-muted-foreground hover:text-primary"
                    >
                      <Image className="w-3.5 h-3.5" />
                    </a>
                  )}
                  {l.id && (
                    <button
                      data-testid={`ledger-delete-${l.id}`}
                      onClick={() => del(l.id)}
                      className="text-muted-foreground hover:text-red-500"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </td>
              </tr>)}</tbody></table>
            {!d.ledger.length && <Empty text={t("noData")} />}
          </Bento>
        </div>
      )}
    </div>
  );
}
