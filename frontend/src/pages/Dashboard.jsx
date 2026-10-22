import { useEffect, useState } from "react";
import { Coffee, Banknote, QrCode, TrendingDown, MapPin } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, CartesianGrid, PieChart, Pie, Cell } from "recharts";
import { api } from "../lib/api";
import { fmtRp, today } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { PageHeader, Stat, Bento, DateFilter, Empty } from "../components/common";
import GpsMap from "../components/GpsMap";

const tip = { contentStyle: { borderRadius: 12, border: "1px solid #333", background: "#111", color: "#fff", fontSize: 12 } };
const menuColors = ["#FF6B00", "#F97316", "#EA580C", "#FB923C", "#C2410C", "#FDBA74"];

export default function Dashboard() {
  const { t } = useT();
  const [range, setRange] = useState(null);
  const [d, setD] = useState(null);
  const [gps, setGps] = useState([]);
  const [showMap, setShowMap] = useState(false);

  useEffect(() => {
    if (!range) return;
    const load = () => api.get("/dashboard/summary", { params: range }).then((r) => setD(r.data)).catch(() => {});
    load(); const id = setInterval(load, 15000); return () => clearInterval(id);
  }, [range]);
  useEffect(() => {
    const load = () => api.get("/gps/active", { params: { date: today() } }).then((r) => setGps(r.data)).catch(() => {});
    load(); const id = setInterval(load, 20000); return () => clearInterval(id);
  }, []);

  return (
    <div data-testid="main-dashboard">
      <PageHeader eyebrow="SI FOUR AM" title={t("dashboard")}><DateFilter onChange={setRange} /></PageHeader>
      {d && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          <Stat gold label="Total Pemasukan" value={fmtRp((d.cash || 0) + (d.qris || 0))} sub={`${d.transactions} POS transactions`} icon={Coffee} testId="stat-total-income" />
          <Stat label={t("expenses")} value={fmtRp(d.expenses)} sub={`Invoices: ${fmtRp(d.invoice_income)}`} icon={TrendingDown} testId="stat-expenses" />
          <Stat label={t("cashRevenue")} value={fmtRp(d.cash)} icon={Banknote} testId="stat-cash" />
          <Stat label={t("qrisRevenue")} value={fmtRp(d.qris)} icon={QrCode} testId="stat-qris" />

          <Bento className="col-span-2 lg:col-span-2 fade-up" testId="chart-rider-sales">
            <p className="eyebrow mb-4">5 Penjualan Rider Tertinggi</p>
            {d.by_rider.length ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={d.by_rider.slice(0, 5).map((r) => ({ name: r.rider_name.split(" ")[0], cash: r.cash, qris: r.qris }))}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis hide /><Tooltip {...tip} formatter={(v) => fmtRp(v)} />
                  <Bar dataKey="cash" stackId="a" fill="#FF6B00" radius={[0, 0, 6, 6]} /><Bar dataKey="qris" stackId="a" fill="#F97316" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <Empty text={t("noData")} />}
          </Bento>
          <Bento className="col-span-2 fade-up" testId="dashboard-menu-donut">
            <p className="eyebrow mb-4">Menu / Produk Terjual</p>
            {d.by_menu.length ? <div className="flex items-center gap-4"><ResponsiveContainer width="52%" height={240}><PieChart><Pie data={d.by_menu} dataKey="qty" nameKey="name" innerRadius={58} outerRadius={90} paddingAngle={3}>{d.by_menu.map((row, index) => <Cell key={row.name} fill={menuColors[index % menuColors.length]} />)}</Pie><Tooltip {...tip} formatter={(value, name) => [`${value} cup`, name]} /></PieChart></ResponsiveContainer><div className="flex-1 text-xs space-y-2">{d.by_menu.slice(0, 5).map((row, index) => <div key={row.name} className="flex justify-between gap-2"><span className="truncate flex items-center gap-2"><span className="w-2 h-2 rounded-full shrink-0" style={{ background: menuColors[index % menuColors.length] }} />{row.name}</span><b className="num">{row.qty}</b></div>)}</div></div> : <Empty text={t("noData")} />}
          </Bento>
          <Bento className="col-span-2 fade-up" testId="chart-money-flow">
            <p className="eyebrow mb-4">{t("income")} vs {t("outgo")}</p>
            {d.by_date.length ? (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={d.by_date.map((x) => ({ date: x.date.slice(5), in: x.cash + x.qris, out: x.expenses }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#3333" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis hide /><Tooltip {...tip} formatter={(v) => fmtRp(v)} />
                  <Area type="monotone" dataKey="in" stroke="#FF6B00" fill="#FF6B0033" strokeWidth={2} /><Area type="monotone" dataKey="out" stroke="#ef4444" fill="#ef444422" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : <Empty text={t("noData")} />}
          </Bento>

          <Bento className="col-span-2 fade-up" testId="rider-table">
            <div className="flex items-center justify-between mb-4"><p className="eyebrow">Riders</p><span className="text-xs text-muted-foreground flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />realtime · click for GPS</span></div>
            <table className="table-x"><thead><tr><th>Rider</th><th>Cups</th><th>Cash</th><th>QRIS</th><th>Total</th></tr></thead>
              <tbody>{d.by_rider.map((r) => (
                <tr key={r.rider_id} data-testid={`rider-row-${r.rider_id}`} onClick={() => setShowMap(true)} className="cursor-pointer hover:bg-muted/50 transition-colors">
                  <td className="font-semibold">{r.rider_name}</td><td className="num">{r.cups}</td><td className="num">{fmtRp(r.cash)}</td><td className="num">{fmtRp(r.qris)}</td><td data-testid={`rider-total-${r.rider_id}`} className="num font-bold text-primary">{fmtRp(r.cash + r.qris)}</td></tr>))}
                {!d.by_rider.length && <tr><td colSpan={5}><Empty text={t("noData")} /></td></tr>}
              </tbody></table>
          </Bento>
          <Bento gold className="col-span-2 fade-up" testId="gps-panel">
            <div className="flex items-center justify-between mb-4"><p className="eyebrow flex items-center gap-2"><MapPin className="w-3.5 h-3.5 text-primary" />{t("activeRiders")} · {gps.length}</p>
              <button data-testid="toggle-map-button" onClick={() => setShowMap(!showMap)} className="text-xs font-semibold text-primary">{showMap ? "Hide map" : "Show map"}</button></div>
            {showMap ? <GpsMap points={gps} height={300} /> : (
              <div className="space-y-2">{gps.map((g) => <div key={g.rider_id} className="flex justify-between text-sm"><span>{g.rider_name}</span><span className="num text-muted-foreground">{g.lat.toFixed(4)}, {g.lng.toFixed(4)}</span></div>)}
                {!gps.length && <Empty text="No riders on duty right now" />}</div>)}
          </Bento>
        </div>
      )}
    </div>
  );
}
