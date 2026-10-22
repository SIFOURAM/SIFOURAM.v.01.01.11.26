import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { fmtRp } from "../lib/helpers";
import { Bento, DateFilter, PageHeader, Stat } from "../components/common";

export default function POSDashboard() {
  const [range, setRange] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!range) return;
    setLoading(true);
    setError("");
    api.get("/reports/sales", { params: { ...range, payment_method: "all", order_type: "all" } })
      .then((response) => setReport(response.data))
      .catch(() => {
        setReport(null);
        setError("Gagal memuat ringkasan POS. Coba pilih periode kembali.");
      })
      .finally(() => setLoading(false));
  }, [range]);

  const payment = Object.fromEntries((report?.payment_distribution || []).map((row) => [row.name.toLowerCase(), row.value]));
  return (
    <div data-testid="pos-dashboard-page">
      <PageHeader>
        <DateFilter onChange={setRange} />
      </PageHeader>
      {loading && <p data-testid="pos-dashboard-loading" className="text-sm text-muted-foreground py-6">Memuat ringkasan POS...</p>}
      {error && <p data-testid="pos-dashboard-error" className="text-sm text-red-500 py-6">{error}</p>}
      {report && <><div className="grid grid-cols-2 gap-4">
        <Stat testId="pos-dashboard-sales" gold className="col-span-2" label="Total Penjualan" value={fmtRp(report.revenue)} />
        <Stat testId="pos-dashboard-cash" label="Total Tunai" value={fmtRp(payment.cash || 0)} />
        <Stat testId="pos-dashboard-qris" label="Total QRIS" value={fmtRp(payment.qris || 0)} />
      </div>
      <Bento scrollable testId="pos-dashboard-history" className="mt-4 overflow-x-auto">
        <p className="eyebrow mb-4">History Penjualan</p>
        <table className={report.daily_revenue.length ? "table-x min-w-[38rem]" : "table-x w-full"}><thead><tr><th>Tanggal</th><th className="text-right">Total Penjualan</th></tr></thead>
          <tbody>{report.daily_revenue.length ? report.daily_revenue.map((row) => <tr key={row.date}><td>{row.date}</td><td className="text-right num">{fmtRp(row.revenue)}</td></tr>) : <tr><td colSpan="2" className="text-center text-muted-foreground py-8">Belum ada penjualan pada periode ini.</td></tr>}</tbody>
        </table>
      </Bento></>}
    </div>
  );
}