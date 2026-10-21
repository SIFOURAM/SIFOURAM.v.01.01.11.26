import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { fmtRp } from "../lib/helpers";
import { Bento, DateFilter, PageHeader, Stat } from "../components/common";

export default function POSDashboard() {
  const [range, setRange] = useState(null);
  const [report, setReport] = useState(null);

  useEffect(() => {
    if (!range) return;
    api.get("/reports/sales", { params: { ...range, payment_method: "all", order_type: "all" } })
      .then((response) => setReport(response.data))
      .catch(() => setReport(null));
  }, [range]);

  const payment = Object.fromEntries((report?.payment_distribution || []).map((row) => [row.name.toLowerCase(), row.value]));
  return (
    <div data-testid="pos-dashboard-page">
      <PageHeader>
        <DateFilter onChange={setRange} />
      </PageHeader>
      {report && <><div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Stat testId="pos-dashboard-cash" label="Total Tunai" value={fmtRp(payment.cash || 0)} />
        <Stat testId="pos-dashboard-qris" label="Total QRIS" value={fmtRp(payment.qris || 0)} />
        <Stat testId="pos-dashboard-sales" gold label="Total Penjualan" value={fmtRp(report.revenue)} />
      </div>
      <Bento testId="pos-dashboard-history" className="mt-4 overflow-x-auto">
        <p className="eyebrow mb-4">History Penjualan</p>
        <table className="table-x min-w-[38rem]"><thead><tr><th>Tanggal</th><th className="text-right">Total Penjualan</th></tr></thead>
          <tbody>{report.daily_revenue.map((row) => <tr key={row.date}><td>{row.date}</td><td className="text-right num">{fmtRp(row.revenue)}</td></tr>)}</tbody>
        </table>
      </Bento></>}
    </div>
  );
}