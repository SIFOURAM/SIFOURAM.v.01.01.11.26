import { useEffect, useMemo, useState } from "react";
import { FileDown, FileSpreadsheet, Printer } from "lucide-react";
import { Bar, BarChart, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";
import { api } from "../lib/api";
import { fmtRp } from "../lib/helpers";
import { Bento, DateFilter, Empty, PageHeader, Select, Stat } from "../components/common";

const COLORS = ["#FF6B00", "#FFD700", "#16a34a", "#2563eb", "#dc2626", "#9333ea"];
const tooltip = { contentStyle: { borderRadius: 8, border: "1px solid #444", fontSize: 12 } };

export default function Reports() {
  const [range, setRange] = useState(null);
  const [method, setMethod] = useState("all");
  const [orderType, setOrderType] = useState("all");
  const [view, setView] = useState("sales");
  const [report, setReport] = useState(null);

  useEffect(() => {
    if (!range) return;
    api.get("/reports/sales", { params: { ...range, payment_method: method, order_type: orderType } })
      .then((response) => setReport(response.data))
      .catch(() => setReport(null));
  }, [range, method, orderType]);

  const title = view === "sales" ? "Laporan Penjualan" : "Performa Produk";
  const productRows = useMemo(() => report?.products || [], [report]);
  const exportExcel = () => {
    if (!report) return;
    const workbook = XLSX.utils.book_new();
    const summary = [
      ["SI FOUR AM", title],
      ["Periode", `${range.start} s/d ${range.end}`],
      ["Total transaksi", report.transactions],
      ["Total revenue", report.revenue],
      ["Rata-rata order", report.average_order],
      ["Total diskon", report.discount],
    ];
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(summary), "Ringkasan");
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(productRows.map((row) => ({
        Peringkat: row.rank,
        Produk: row.name,
        Kuantitas: row.qty,
        Revenue: row.revenue,
      }))),
      "Produk",
    );
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(report.daily_revenue.map((row) => ({ Tanggal: row.date, Revenue: row.revenue }))),
      "Tren Harian",
    );
    XLSX.writeFile(workbook, `SIFOURAM_${view}_${range.start}_${range.end}.xlsx`);
  };
  const exportPdf = () => {
    if (!report) return;
    const doc = new jsPDF({ orientation: "landscape", format: "a4" });
    doc.setFontSize(15);
    doc.text(`SI FOUR AM — ${title}`, 14, 15);
    doc.setFontSize(9);
    doc.text(`${range.start} s/d ${range.end}`, 14, 21);
    autoTable(doc, {
      startY: 27,
      head: [["Transaksi", "Revenue", "Rata-rata Order", "Diskon"]],
      body: [[
        report.transactions,
        fmtRp(report.revenue),
        fmtRp(report.average_order),
        fmtRp(report.discount),
      ]],
      styles: { fontSize: 8 },
      headStyles: { fillColor: [255, 107, 0] },
      theme: "grid",
    });
    autoTable(doc, {
      head: [["Rank", "Produk", "Kuantitas", "Revenue"]],
      body: productRows.map((row) => [row.rank, row.name, row.qty, fmtRp(row.revenue)]),
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [255, 215, 0], textColor: [0, 0, 0] },
      theme: "grid",
    });
    doc.save(`SIFOURAM_${view}_${range.start}_${range.end}.pdf`);
  };

  return (
    <div data-testid="reports-page">
      <PageHeader>
        <div className="flex gap-1 border border-border p-1 rounded-lg">
          <button data-testid="report-sales-tab" onClick={() => setView("sales")} className={`h-8 px-3 text-xs font-bold rounded ${view === "sales" ? "bg-primary text-white" : ""}`}>Penjualan</button>
          <button data-testid="report-products-tab" onClick={() => setView("products")} className={`h-8 px-3 text-xs font-bold rounded ${view === "products" ? "bg-primary text-white" : ""}`}>Produk</button>
        </div>
        <Select data-testid="report-payment-filter" className="w-32 h-9 text-xs" value={method} onChange={setMethod} options={[{ value: "all", label: "Semua bayar" }, { value: "cash", label: "Cash" }, { value: "qris", label: "QRIS" }]} />
        <Select data-testid="report-type-filter" className="w-32 h-9 text-xs" value={orderType} onChange={setOrderType} options={[{ value: "all", label: "Semua order" }, { value: "regular", label: "Reguler" }, { value: "bundling", label: "Bundling" }]} />
        <DateFilter onChange={setRange} />
        {report && <div className="flex gap-1">
          <button data-testid="report-excel-button" onClick={exportExcel} className="btn-ghost h-9 px-3 text-xs"><FileSpreadsheet className="w-3.5 h-3.5" />Excel</button>
          <button data-testid="report-pdf-button" onClick={exportPdf} className="btn-ghost h-9 px-3 text-xs"><FileDown className="w-3.5 h-3.5" />PDF</button>
          <button data-testid="report-print-button" onClick={exportPdf} className="btn-ghost h-9 px-3 text-xs"><Printer className="w-3.5 h-3.5" />Cetak</button>
        </div>}
      </PageHeader>
      {report && <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat testId="report-transactions" label="Total transaksi" value={report.transactions} />
        <Stat testId="report-revenue" gold label="Total revenue" value={fmtRp(report.revenue)} />
        <Stat testId="report-average" label="Rata-rata order" value={fmtRp(report.average_order)} />
        <Stat testId="report-discount" label="Total diskon" value={fmtRp(report.discount)} />
        {view === "sales" && <>
          <Bento testId="report-revenue-trend" className="col-span-2 fade-up">
            <p className="eyebrow mb-4">Tren revenue harian</p>
            {report.daily_revenue.length ? <ResponsiveContainer width="100%" height={250}><LineChart data={report.daily_revenue}><XAxis dataKey="date" tick={{ fontSize: 10 }} /><YAxis hide /><Tooltip {...tooltip} formatter={(value) => fmtRp(value)} /><Line type="monotone" dataKey="revenue" stroke="#FF6B00" strokeWidth={3} /></LineChart></ResponsiveContainer> : <Empty text="Belum ada transaksi pada periode ini" />}
          </Bento>
          <Distribution title="Metode pembayaran" testId="report-payment-distribution" rows={report.payment_distribution} />
          <Distribution title="Tipe pesanan" testId="report-order-distribution" rows={report.order_distribution} />
          <Bento testId="report-hourly" className="col-span-2 fade-up">
            <p className="eyebrow mb-4">Transaksi & revenue per jam</p>
            {report.hourly.length ? <ResponsiveContainer width="100%" height={250}><BarChart data={report.hourly}><XAxis dataKey="hour" tick={{ fontSize: 10 }} /><YAxis hide /><Tooltip {...tooltip} formatter={(value) => fmtRp(value)} /><Bar dataKey="revenue" fill="#FF6B00" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer> : <Empty text="Belum ada transaksi pada periode ini" />}
          </Bento>
        </>}
        <Bento testId="report-products-table" className="col-span-2 lg:col-span-4 fade-up overflow-x-auto">
          <p className="eyebrow mb-4">{view === "sales" ? "Produk terlaris" : "Performa produk"}</p>
          <table className="table-x min-w-[34rem]"><thead><tr><th>Rank</th><th>Produk</th><th className="text-right">Kuantitas</th><th className="text-right">Revenue</th></tr></thead>
            <tbody>{productRows.map((row) => <tr key={row.name}><td className="num">{row.rank}</td><td className="font-semibold">{row.name}</td><td className="num text-right">{row.qty}</td><td className="num text-right">{fmtRp(row.revenue)}</td></tr>)}</tbody>
          </table>
          {!productRows.length && <Empty text="Belum ada produk terjual pada periode ini" />}
        </Bento>
      </div>}
    </div>
  );
}

function Distribution({ title, rows, testId }) {
  return (
    <Bento testId={testId} className="col-span-2 lg:col-span-1 fade-up">
      <p className="eyebrow mb-4">{title}</p>
      {rows.length ? <ResponsiveContainer width="100%" height={180}><PieChart><Pie data={rows} dataKey="value" nameKey="name" innerRadius={40} outerRadius={70}>{rows.map((row, index) => <Cell key={row.name} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip {...tooltip} formatter={(value) => fmtRp(value)} /></PieChart></ResponsiveContainer> : <Empty text="Tidak ada data" />}
    </Bento>
  );
}