import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { FileDown, FileSpreadsheet, Printer } from "lucide-react";
import { Bar, BarChart, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";
import { api, errMsg } from "../lib/api";
import { fmtRp } from "../lib/helpers";
import { Bento, DateFilter, Empty, PageHeader, Stat } from "../components/common";

const COLORS = ["#FF6B00", "#F97316", "#EA580C", "#FB923C", "#C2410C", "#FDBA74"];
const tooltip = { contentStyle: { borderRadius: 8, border: "1px solid #444", fontSize: 12 } };
const REPORT_TABS = [
  ["sales", "Penjualan"],
  ["products", "Produk"],
  ["wastage", "Waste"],
  ["inventory", "Persediaan"],
  ["purchases", "Pembelian"],
  ["opname", "Opname"],
];

export default function Reports() {
  const [range, setRange] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState(searchParams.get("view") || "sales");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { setView(searchParams.get("view") || "sales"); }, [searchParams]);
  const selectView = (nextView) => { setView(nextView); setSearchParams({ view: nextView }); };

  useEffect(() => {
    if (!range || !["sales", "products"].includes(view)) return;
    setLoading(true);
    setError("");
    api.get("/reports/sales", { params: range })
      .then((response) => setReport(response.data))
      .catch((requestError) => {
        setReport(null);
        setError(errMsg(requestError));
      })
      .finally(() => setLoading(false));
  }, [range, view]);

  const title = view === "sales" ? "Laporan Penjualan" : "Performa Produk";
  const productRows = useMemo(() => report?.products || [], [report]);
  if (!["sales", "products"].includes(view)) {
    return <OperationsReport kind={view} setView={selectView} />;
  }
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
  const buildPdf = () => {
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
      headStyles: { fillColor: [255, 107, 0], textColor: [255, 255, 255] },
      theme: "grid",
    });
    return doc;
  };
  const exportPdf = () => {
    const doc = buildPdf();
    if (doc) doc.save(`SIFOURAM_${view}_${range.start}_${range.end}.pdf`);
  };
  const printPdf = () => {
    const doc = buildPdf();
    if (doc) window.open(doc.output("bloburl"), "_blank", "noopener,noreferrer");
  };

  return (
    <div data-testid="reports-page">
      <PageHeader title={title}>
        <div className="w-full flex flex-col gap-3">
          <div className="w-full space-y-2">
            {report && <div className="flex gap-1" data-testid="report-export-actions">
              <button data-testid="report-excel-button" onClick={exportExcel} className="btn-ghost h-9 px-3 text-xs"><FileSpreadsheet className="w-3.5 h-3.5" />Excel</button>
              <button data-testid="report-pdf-button" onClick={exportPdf} className="btn-ghost h-9 px-3 text-xs"><FileDown className="w-3.5 h-3.5" />PDF</button>
              <button data-testid="report-print-button" onClick={printPdf} className="btn-ghost h-9 px-3 text-xs"><Printer className="w-3.5 h-3.5" />Cetak</button>
            </div>}
            <div className="flex flex-wrap items-start gap-2">
              <DateFilter onChange={setRange} />
            </div>
          </div>
        </div>
      </PageHeader>
      {loading && <p data-testid="reports-loading" className="text-sm text-muted-foreground py-8">Memuat laporan...</p>}
      {error && <p data-testid="reports-error" className="text-sm text-red-500 py-8">Gagal memuat laporan: {error}</p>}
      {report && <><div className="grid grid-cols-2 gap-4">
        <Stat testId="report-transactions" label="Total transaksi" value={report.transactions} />
        <Stat testId="report-revenue" gold label="Total revenue" value={fmtRp(report.revenue)} />
      </div><ReportFilterSummary report={report} /><div className="grid grid-cols-2 gap-4 mt-4">
        <Stat testId="report-average" label="Rata-rata order" value={fmtRp(report.average_order)} />
        <Stat testId="report-discount" label="Total diskon" value={fmtRp(report.discount)} />
      </div><div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
        {view === "sales" && <>
          <Bento testId="report-revenue-trend" className="col-span-2 fade-up">
            <p className="eyebrow mb-4">Tren revenue harian</p>
            {report.daily_revenue.length ? <ResponsiveContainer width="100%" height={250}><LineChart data={report.daily_revenue}><XAxis dataKey="date" tick={{ fontSize: 10 }} /><YAxis hide /><Tooltip {...tooltip} formatter={(value) => fmtRp(value)} /><Line type="monotone" dataKey="revenue" stroke="#FF6B00" strokeWidth={3} /></LineChart></ResponsiveContainer> : <Empty text="Belum ada transaksi pada periode ini" />}
          </Bento>
          <Distribution title="Metode pembayaran" testId="report-payment-distribution" rows={report.payment_distribution} />
          <Distribution title="Tipe pesanan" testId="report-order-distribution" rows={report.order_distribution} />
          <Distribution title="Layanan pesanan" testId="report-service-distribution" rows={report.service_distribution} />
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
      </div></>}
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

function ReportFilterSummary({ report }) {
  const amount = (rows, name) => rows.find((row) => row.name.toLowerCase() === name)?.value || 0;
  return (
    <div className="grid grid-cols-2 gap-4 mt-4">
      <Bento testId="report-cash-summary" className="fade-up">
        <p className="eyebrow">Pembayaran Cash</p>
        <p className="mt-2 num text-sm font-bold">{fmtRp(amount(report.payment_distribution, "cash"))}</p>
      </Bento>
      <Bento testId="report-qris-summary" className="fade-up">
        <p className="eyebrow">Pembayaran QRIS</p>
        <p className="mt-2 num text-sm font-bold">{fmtRp(amount(report.payment_distribution, "qris"))}</p>
      </Bento>
      <Bento testId="report-regular-summary" className="fade-up">
        <p className="eyebrow">Reguler</p>
        <p className="mt-2 num text-sm font-bold">{fmtRp(amount(report.order_distribution, "regular"))}</p>
      </Bento>
      <Bento testId="report-bundling-summary" className="fade-up">
        <p className="eyebrow">Bundling</p>
        <p className="mt-2 num text-sm font-bold">{fmtRp(amount(report.order_distribution, "bundling"))}</p>
      </Bento>
      <Bento testId="report-dine-in-summary" className="fade-up">
        <p className="eyebrow">Dine In</p>
        <p className="mt-2 num text-sm font-bold">{fmtRp(amount(report.service_distribution, "dine_in"))}</p>
      </Bento>
      <Bento testId="report-takeaway-summary" className="fade-up">
        <p className="eyebrow">Takeaway</p>
        <p className="mt-2 num text-sm font-bold">{fmtRp(amount(report.service_distribution, "takeaway"))}</p>
      </Bento>
      <Bento testId="report-online-summary" className="fade-up">
        <p className="eyebrow">Online</p>
        <p className="mt-2 num text-sm font-bold">{fmtRp(amount(report.service_distribution, "online"))}</p>
      </Bento>
    </div>
  );
}

function OperationsReport({ kind, setView }) {
  const [range, setRange] = useState(() => {
    const date = new Date().toISOString().slice(0, 10);
    return { start: date, end: date };
  });
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const labels = {
    wastage: "Laporan Waste",
    inventory: "Nilai Persediaan",
    purchases: "Pembelian",
    opname: "Laporan Stok Opname",
  };
  useEffect(() => {
    if (!range) return;
    setError("");
    api.get("/reports/operations", { params: { kind, ...range } })
      .then((response) => setData(response.data))
      .catch((requestError) => {
        setData(null);
        setError(errMsg(requestError));
      });
  }, [kind, range]);

  const rows = data?.rows || [];
  const summary = data?.summary || {};
  const columns = operationColumns(kind);
  const exportExcel = () => {
    if (!data) return;
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(rows.map((row) => operationRow(kind, row))),
      labels[kind],
    );
    XLSX.writeFile(workbook, `SIFOURAM_${kind}_${range.start}_${range.end}.xlsx`);
  };
  const printPdf = (save = false) => {
    if (!data) return;
    const doc = new jsPDF({ orientation: "landscape", format: "a4" });
    doc.setFontSize(15);
    doc.text(`SI FOUR AM — ${labels[kind]}`, 14, 15);
    doc.setFontSize(9);
    doc.text(`${range.start} s/d ${range.end}`, 14, 21);
    autoTable(doc, {
      startY: 27,
      head: [columns.map((column) => column.label)],
      body: rows.map((row) => columns.map((column) => column.format(row))),
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [255, 107, 0] },
      theme: "grid",
    });
    if (save) doc.save(`SIFOURAM_${kind}_${range.start}_${range.end}.pdf`);
    else window.open(doc.output("bloburl"), "_blank", "noopener,noreferrer");
  };

  return (
    <div data-testid={`operations-report-${kind}`}>
      <PageHeader title={labels[kind]}>
        {kind !== "inventory" && <DateFilter onChange={setRange} />}
        {data && <div className="flex gap-1"><button data-testid="operations-excel" onClick={exportExcel} className="btn-ghost h-9 px-3 text-xs"><FileSpreadsheet className="w-3.5 h-3.5" />Excel</button><button data-testid="operations-pdf" onClick={() => printPdf(true)} className="btn-ghost h-9 px-3 text-xs"><FileDown className="w-3.5 h-3.5" />PDF</button><button data-testid="operations-print" onClick={() => printPdf(false)} className="btn-ghost h-9 px-3 text-xs"><Printer className="w-3.5 h-3.5" />Cetak</button></div>}
      </PageHeader>
      {error && <p data-testid="operations-error" className="text-sm text-red-500 py-8">Gagal memuat laporan: {error}</p>}
      {data && <><div className="grid grid-cols-2 lg:grid-cols-4 gap-4"><OperationsSummary kind={kind} summary={summary} /></div><Bento testId="operations-table" className="mt-4 overflow-x-auto"><table className={kind === "inventory" ? "table-x w-full table-fixed" : "table-x min-w-[28rem]"}>{kind === "inventory" && <colgroup><col className="w-1/2" /><col className="w-1/4" /><col className="w-1/4" /></colgroup>}<thead><tr>{columns.map((column) => <th key={column.key} className={column.right ? "text-right whitespace-nowrap" : ""}>{column.label}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.id || row.name}>{columns.map((column) => <td key={column.key} className={`${column.right ? "text-right num whitespace-nowrap" : ""} ${kind === "inventory" && column.key === "name" ? "truncate" : ""}`}>{column.render ? column.render(row) : column.format(row)}</td>)}</tr>)}</tbody></table>{!rows.length && <Empty text="Belum ada data pada periode ini" />}</Bento></>}
    </div>
  );
}

function OperationsSummary({ kind, summary }) {
  if (kind === "wastage") return <><Stat testId="waste-value" gold label="Nilai terbuang" value={fmtRp(summary.total_value)} /><Stat testId="waste-count" label="Jumlah catatan" value={summary.count || 0} /><Stat testId="waste-reason" label="Alasan terbesar" value={summary.largest_reason || "—"} /><Stat testId="waste-reason-value" label="Nilai alasan terbesar" value={fmtRp(summary.largest_reason_value)} /></>;
  if (kind === "inventory") return <><Stat testId="inventory-total-value" gold label="Total nilai persediaan" value={fmtRp(summary.total_value)} /><Stat testId="inventory-product-value" label="Produk" value={fmtRp(summary.product_value)} /><Stat testId="inventory-material-value" label="Bahan baku" value={fmtRp(summary.material_value)} /><Stat testId="inventory-items" label="Jumlah barang" value={summary.item_count || 0} /></>;
  if (kind === "purchases") return <><Stat testId="purchase-total" gold label="Total pembelian" value={fmtRp(summary.total_cost)} /><Stat testId="purchase-count" label="Jumlah penerimaan" value={summary.count || 0} /><Stat testId="purchase-suppliers" label="Supplier" value={summary.supplier_count || 0} /></>;
  return <><Stat testId="opname-count" gold label="Opname" value={summary.count || 0} /><Stat testId="opname-accuracy" label="Akurasi stok" value={summary.accuracy === null ? "—" : `${summary.accuracy}%`} /><Stat testId="opname-positive" label="Selisih lebih" value={fmtRp(summary.positive_value)} /><Stat testId="opname-negative" label="Selisih kurang" value={fmtRp(summary.negative_value)} /></>;
}

function operationColumns(kind) {
  if (kind === "wastage") return [{ key: "date", label: "Tanggal", format: (row) => row.date }, { key: "menu", label: "Produk", format: (row) => row.menu_name }, { key: "qty", label: "Qty", right: true, format: (row) => row.qty }, { key: "reason", label: "Alasan", format: (row) => row.reason }, { key: "value", label: "Nilai", right: true, format: (row) => fmtRp(row.value) }];
  if (kind === "inventory") return [{ key: "name", label: "Barang", format: (row) => row.name }, { key: "qty", label: "Qty", right: true, format: (row) => `${row.qty} ${row.unit}`, render: (row) => <div className="flex justify-between gap-1"><span>{row.qty}</span><span className="text-muted-foreground">{row.unit}</span></div> }, { key: "value", label: "Nilai", right: true, format: (row) => fmtRp(row.value), render: (row) => <div className="flex justify-between gap-1"><span>Rp</span><span>{fmtRp(row.value).replace("Rp", "").trim()}</span></div> }];
  if (kind === "purchases") return [{ key: "date", label: "Tanggal", format: (row) => row.date }, { key: "material", label: "Bahan", format: (row) => row.material_name }, { key: "item", label: "Item", format: (row) => row.item_name || "—" }, { key: "supplier", label: "Supplier", format: (row) => row.supplier || "—" }, { key: "qty", label: "Qty", right: true, format: (row) => `${row.qty} ${row.unit}` }, { key: "cost", label: "Nilai", right: true, format: (row) => fmtRp(row.cost) }];
  return [{ key: "date", label: "Tanggal", format: (row) => row.date }, { key: "material", label: "Bahan", format: (row) => row.material_name }, { key: "before", label: "Sistem", right: true, format: (row) => row.before }, { key: "after", label: "Fisik", right: true, format: (row) => row.after }, { key: "difference", label: "Selisih", right: true, format: (row) => row.difference }, { key: "value", label: "Nilai selisih", right: true, format: (row) => fmtRp(row.difference_value) }];
}

function operationRow(kind, row) {
  return Object.fromEntries(operationColumns(kind).map((column) => [column.label, column.format(row)]));
}