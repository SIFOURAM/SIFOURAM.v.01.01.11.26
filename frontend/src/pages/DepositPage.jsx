import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { fmtRp, today, fmtDate } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Bento, Field, Select, QtySelect, ReceiptModal, RLine, Empty } from "../components/common";

const EMPTY = { stock: 0, remaining: 0, cash: 0, qris: 0, wastage: 0 };

export default function DepositPage() {
  const { t, lang } = useT();
  const { user } = useAuth();
  const [riders, setRiders] = useState([]);
  const [menus, setMenus] = useState([]);
  const [riderId, setRiderId] = useState("");
  const [date, setDate] = useState(today());
  const [rows, setRows] = useState({});
  const [debt, setDebt] = useState(0);
  const [eod, setEod] = useState(null);
  const [result, setResult] = useState(null);
  const [list, setList] = useState([]);
  const [busy, setBusy] = useState(false);

  const loadList = () => api.get("/deposits", { params: { start: "2000-01-01", end: "2100-01-01" } }).then((r) => setList(r.data.slice(0, 20)));
  useEffect(() => { api.get("/users", { params: { role: "rider" } }).then((r) => setRiders(r.data)); api.get("/menus").then((r) => setMenus(r.data)); loadList(); }, []);

  useEffect(() => {
    if (!riderId || !menus.length) {
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const [existing, salesEod, debtResult] = await Promise.all([
          api.get("/deposits", {
            params: { start: date, end: date, rider_id: riderId },
          }),
          api.get("/sales/eod", { params: { rider_id: riderId, date } }),
          api.get("/deposits/debt", { params: { rider_id: riderId, date } }),
        ]);
        if (cancelled) {
          return;
        }
        const previous = existing.data[0];
        const eodRows = Object.fromEntries(
          salesEod.data.rows.map((row) => [row.menu_id, row]),
        );
        const nextRows = {};
        menus.forEach((menu) => {
          const sale = eodRows[menu.id];
          const priorRow = previous?.rows.find((row) => row.menu_id === menu.id);
          nextRows[menu.id] = {
            stock: priorRow?.stock ?? sale?.initial ?? 0,
            remaining: priorRow?.remaining ?? Math.max(0, sale?.remaining || 0),
            cash: priorRow?.cash ?? sale?.cash_qty ?? 0,
            qris: priorRow?.qris ?? sale?.qris_qty ?? 0,
            wastage: priorRow?.wastage || 0,
          };
        });
        setEod(salesEod.data);
        setDebt(debtResult.data.debt);
        setRows(nextRows);
      } catch (error) {
        if (!cancelled) {
          toast.error(errMsg(error));
          setEod(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [riderId, date, menus]);

  const calc = useMemo(() => {
    let minus = 0;
    let wastage = 0;
    const lines = menus.map((menu) => {
      const row = rows[menu.id] || EMPTY;
      const sold = row.cash + row.qris;
      const diff = row.stock - (sold + row.remaining + row.wastage);
      minus += Math.max(0, diff) * menu.price;
      wastage += row.wastage;
      return { ...menu, ...row, sold, diff };
    });
    const cash = lines.reduce((total, line) => total + line.cash * line.price, 0);
    const qris = lines.reduce((total, line) => total + line.qris * line.price, 0);
    const cups = lines.reduce((total, line) => total + line.sold, 0);
    return {
      lines,
      cups,
      cash,
      qris,
      minus,
      wastage,
      income: cash + qris,
      remainingDebt: debt + minus,
      net: cash,
    };
  }, [rows, menus, debt]);

  const setCell = (mid, key, value) => {
    const current = rows[mid] || EMPTY;
    const next = { ...current, [key]: value };
    next.stock = Math.max(0, next.stock);
    next.cash = Math.min(Math.max(0, next.cash), next.stock);
    next.qris = Math.min(Math.max(0, next.qris), next.stock - next.cash);
    const sold = next.cash + next.qris;
    const maxRemaining = Math.max(0, next.stock - sold);
    next.remaining = Math.min(Math.max(0, next.remaining), maxRemaining);
    const available = Math.max(0, next.stock - sold - next.remaining);
    next.wastage = Math.min(Math.max(0, next.wastage), available);
    setRows({ ...rows, [mid]: next });
  };

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/deposits", {
        rider_id: riderId,
        date,
        pic_id: user.id,
        rows: menus.map((menu) => ({
          menu_id: menu.id,
          stock: rows[menu.id]?.stock || 0,
          remaining: rows[menu.id]?.remaining || 0,
          cash: rows[menu.id]?.cash || 0,
          qris: rows[menu.id]?.qris || 0,
          wastage: rows[menu.id]?.wastage || 0,
        })),
      });
      setResult(data);
      toast.success(t("save") + " ✓");
      loadList();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  const reset = () => {
    setResult(null);
    setRiderId("");
    setRows({});
  };

  const L = lang === "id";
  const waText = result && `*SI FOUR AM ${L ? "SETORAN" : "DEPOSIT"}*\n----------------------------------\n👤 *Rider:* ${result.rider_name}\n👥 *PIC:* ${result.pic_name}\n📅 *${L ? "Tanggal" : "Date"}:* ${fmtDate(result.date)} ${result.time} WIB\n📊 *${L ? "Total Terjual" : "Total Sold"}:* ${result.total_cups} cups\n🗑️ *${L ? "Total Wastage" : "Total Wastage"}:* ${result.total_wastage}\n\n💰 *Total Cash:* ${fmtRp(result.total_cash)}\n💳 *Total QRIS:* ${fmtRp(result.total_qris)}\n\n🧾 *${L ? "Hutang Awal" : "Initial Debt"}:* ${fmtRp(result.initial_debt)}\n⚠️ *${L ? "Hutang Baru" : "New Debt"}:* ${fmtRp(result.new_debt)}\n📈 *${L ? "Bayar Hutang" : "Debt Payment"}:* ${fmtRp(result.debt_payment)}\n❗ *${L ? "Sisa Hutang" : "Remaining Debt"}:* ${fmtRp(result.remaining_debt)}\n\n💵 *${L ? "Komisi Rider" : "Rider Commission"}:* ${fmtRp(result.commission)}\n📉 *${L ? "Pengeluaran" : "Expenses"}:* ${fmtRp(result.expenses)} ${result.expense_note}\n🚀 *${L ? "SETORAN BERSIH" : "NET CASH DEPOSIT"}:* ${fmtRp(result.net_cash)}\n----------------------------------\n${result.motivation}`;

  return (
    <div data-testid="deposit-page">
      <PageHeader eyebrow="Bar Team → Rider" title={t("deposit")} />
      <Bento gold className="fade-up" testId="deposit-form">
        <div className="grid grid-cols-2 gap-3 mb-5">
          <Field label={`${t("pic")} (auto)`}>
            <input
              data-testid="deposit-pic"
              className="field h-9 bg-muted/50 sm:h-10"
              value={user.name}
              readOnly
            />
          </Field>
          <Field label={t("selectRider")}>
            <Select
              testId="deposit-rider-select"
              value={riderId}
              onChange={setRiderId}
              placeholder="—"
              options={riders.map((rider) => ({ value: rider.id, label: rider.name }))}
            />
          </Field>
        </div>
        <div className="mb-5">
          <Field label={t("date")}>
            <input
              data-testid="deposit-date-input"
              type="date"
              className="field"
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </Field>
        </div>
        {riderId && eod && (
          <div
            data-testid="eod-status"
            className={`rounded-xl p-3 text-xs mb-4 ${
              eod.closed
                ? "bg-emerald-500/10 text-emerald-500"
                : "bg-amber-500/10 text-amber-500"
            }`}
          >
            {eod.closed
              ? L
                ? `✓ EOD selesai pada ${fmtDate(date)} — ${eod.transactions} ${
                    t("transactions")
                  }, ${eod.total_cups} cups (${t("cash")} ${fmtRp(eod.total_cash)}, QRIS ${
                    fmtRp(eod.total_qris)
                  })`
                : `✓ EOD closed for ${fmtDate(date)} — ${eod.transactions} ${
                    t("transactions")
                  }, ${eod.total_cups} cups (${t("cash")} ${fmtRp(eod.total_cash)}, QRIS ${
                    fmtRp(eod.total_qris)
                  })`
              : L
                ? "Rider belum menutup penjualan di POS. Setoran baru dapat disimpan setelah EOD selesai."
                : "Rider must end sales in POS before the deposit can be saved."}
          </div>
        )}
        <div>
          <table className="table-x">
            <thead>
              <tr>
                <th>{t("menu")}</th>
                <th>{t("stock")}</th>
                <th>{t("cash")}</th>
                <th>{t("qris")}</th>
                <th>{t("remaining")}</th>
                <th>{t("wastage")}</th>
                <th className="hide-xs">{t("sold")}</th>
                <th className="hide-xs">{t("diff")}</th>
              </tr>
            </thead>
            <tbody>
              {calc.lines.map((line) => (
                <tr key={line.id} data-testid={`deposit-row-${line.id}`}>
                  <td>
                    <p className="font-semibold text-sm leading-tight">
                      {line.name.replace("SI ", "")}
                    </p>
                    <p className="text-[10px] text-muted-foreground num">
                      {fmtRp(line.price)}
                    </p>
                    <p className="num text-[10px] sm:hidden">
                      {t("sold")} {line.sold} · {t("diff")} {line.diff}
                    </p>
                  </td>
                  <td>
                    <QtySelect
                      testId={`deposit-stock-${line.id}`}
                      max={line.max_stock}
                      value={line.stock}
                      onChange={(value) => setCell(line.id, "stock", value)}
                    />
                  </td>
                  <td>
                    <QtySelect
                      testId={`deposit-cash-${line.id}`}
                      max={Math.max(0, line.stock - line.qris)}
                      value={line.cash}
                      onChange={(value) => setCell(line.id, "cash", value)}
                    />
                  </td>
                  <td>
                    <QtySelect
                      testId={`deposit-qris-${line.id}`}
                      max={Math.max(0, line.stock - line.cash)}
                      value={line.qris}
                      onChange={(value) => setCell(line.id, "qris", value)}
                    />
                  </td>
                  <td>
                    <QtySelect
                      testId={`deposit-remaining-${line.id}`}
                      max={Math.max(0, line.stock - line.sold)}
                      value={line.remaining}
                      onChange={(value) => setCell(line.id, "remaining", value)}
                    />
                  </td>
                  <td>
                    <QtySelect
                      testId={`deposit-wastage-${line.id}`}
                      className={line.wastage > 0 ? "text-primary font-bold" : ""}
                      max={Math.max(0, line.stock - line.sold - line.remaining)}
                      value={line.wastage}
                      onChange={(value) => setCell(line.id, "wastage", value)}
                    />
                  </td>
                  <td className="num font-bold hide-xs">{line.sold}</td>
                  <td
                    className={`num font-bold hide-xs ${
                      line.diff > 0
                        ? "text-red-500"
                        : line.diff < 0
                          ? "text-amber-500"
                          : "text-emerald-500"
                    }`}
                  >
                    {line.diff}
                    {line.diff > 0 && (
                      <span className="block text-[10px]">{fmtRp(line.diff * line.price)}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-6">
          {[[t("cash"), fmtRp(calc.cash), "cash"], [t("qris"), fmtRp(calc.qris), "qris"], [t("totalIncome"), fmtRp(calc.income), "income"], [t("totalSold"), `${calc.cups} ${t("cups")}`, "sold"], [t("newDebt"), fmtRp(calc.minus), "minus"], [t("initialDebt"), fmtRp(debt), "debt"], [t("wastage"), `${calc.wastage} ${t("cups")}`, "wastage"], [t("remainingDebt"), fmtRp(calc.remainingDebt), "remaining-debt"]].map(([l, v, id]) => (
            <div key={id} className="rounded-xl bg-muted/60 p-3"><p className="eyebrow">{l}</p><p className="num font-bold text-sm" data-testid={`calc-${id}`}>{v}</p></div>))}
        </div>
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-6 pt-6 border-t border-border/60">
          <div><p className="eyebrow">{t("netCash")}</p><p data-testid="calc-net-cash" className="text-3xl font-bold num font-heading text-primary">{fmtRp(calc.net)}</p></div>
          <button
            data-testid="deposit-save-button"
            onClick={save}
            disabled={!riderId || !eod?.closed || busy}
            className="btn-primary h-12 px-8 w-full sm:w-auto"
          >
            {t("saveDb")}
          </button>
        </div>
      </Bento>

      <Bento className="mt-6" testId="deposit-list">
        <p className="eyebrow mb-3">{t("history")}</p>
        <table className="table-x"><thead><tr><th>{t("date")}</th><th>{t("rider")}</th><th className="hide-sm">{t("pic")}</th><th>Cups</th><th className="hide-xs">{t("cash")}</th><th className="hide-xs">{t("qris")}</th><th>Net</th></tr></thead>
          <tbody>{list.map((d) => <tr key={d.id} className="cursor-pointer hover:bg-muted/40" onClick={() => setResult(d)}><td className="num text-xs">{d.date}<span className="hide-sm"> {d.time || ""}</span></td><td>{d.rider_name}</td><td className="text-xs hide-sm">{d.pic_name}</td><td className="num">{d.total_cups}</td><td className="num hide-xs">{fmtRp(d.total_cash)}</td><td className="num hide-xs">{fmtRp(d.total_qris)}</td><td className="num font-bold">{fmtRp(d.net_cash)}</td></tr>)}</tbody></table>
        {!list.length && <Empty text={t("noData")} />}
      </Bento>

      <ReceiptModal open={!!result} onClose={reset} title={L ? "Struk Setoran" : "Deposit Receipt"} waText={waText} filename={`RECEIPT_${(result?.rider_name || "").replace(/\s+/g, "_")}.png`} testId="deposit-receipt">
        {result && <>
          <RLine l="No" r={result.receipt_no} /><RLine l="Rider" r={result.rider_name} /><RLine l="PIC" r={result.pic_name} /><RLine l={t("date")} r={`${fmtDate(result.date)} · ${result.time || "-"}`} />
          <div className="border-t border-dashed border-gray-300 my-2" />
          {result.rows.filter((r) => r.total_sold || r.stock).map((r) => <RLine key={r.menu_id} l={`${r.name} ×${r.total_sold}`} r={fmtRp(r.cash_amt + r.qris_amt)} />)}
          {(result.bundles || []).map((b, i) => <RLine key={i} l={`${b.name} ×${b.qty} (${b.method.toUpperCase()})`} r={fmtRp(b.amount)} />)}
          <div className="border-t border-dashed border-gray-300 my-2" />
          <RLine l={t("totalSold")} r={`${result.total_cups} cups`} /><RLine l={t("wastage")} r={result.total_wastage} /><RLine l="Cash" r={fmtRp(result.total_cash)} /><RLine l="QRIS" r={fmtRp(result.total_qris)} />
          <RLine l={t("initialDebt")} r={fmtRp(result.initial_debt)} /><RLine l={t("newDebt")} r={fmtRp(result.new_debt)} /><RLine l={t("debtPayment")} r={fmtRp(result.debt_payment)} /><RLine l={t("remainingDebt")} r={fmtRp(result.remaining_debt)} />
          <RLine l={t("commission")} r={fmtRp(result.commission || 0)} /><RLine l={t("expenses")} r={fmtRp(result.expenses)} />
          <RLine bold l={t("netCash").toUpperCase()} r={fmtRp(result.net_cash)} />
          <p className="text-[11px] text-center mt-3 text-gray-600">{result.motivation}</p>
        </>}
      </ReceiptModal>
    </div>
  );
}
