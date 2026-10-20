import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { fmtRp, today, fmtDate } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Bento, Field, Select, DateFilter, Stat, Empty, RLine } from "../components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";

export default function CashHandover() {
  const { t } = useT();
  const { user } = useAuth();
  const [staff, setStaff] = useState([]);
  const [range, setRange] = useState(null);
  const [expected, setExpected] = useState(null);
  const [list, setList] = useState([]);
  const [histRange, setHistRange] = useState(null);
  const [f, setF] = useState({ date: today(), giver_id: "", receiver_id: user.id, received_cash: "", note: "" });
  const [exps, setExps] = useState([{ name: "", amount: "" }]);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(false);
  const [clientId, setClientId] = useState(crypto.randomUUID());

  useEffect(() => { api.get("/users").then((r) => setStaff(r.data.filter((u) => u.role !== "rider"))); }, []);
  useEffect(() => { if (range) api.get("/handovers/expected", { params: range }).then((r) => { setExpected(r.data); setF((x) => ({ ...x, received_cash: r.data.expected_cash })); }); }, [range]);
  const loadHist = () => histRange && api.get("/handovers", { params: histRange }).then((r) => setList(r.data));
  useEffect(() => { loadHist(); }, [histRange]); // eslint-disable-line

  const totalExp = exps.reduce((s, e) => s + Number(e.amount || 0), 0);
  const diff = (expected?.expected_cash || 0) - Number(f.received_cash || 0) - totalExp;

  const save = async () => {
    setBusy(true);
    try {
      await api.post("/handovers", { ...f, received_cash: Number(f.received_cash || 0), expected_cash: expected?.expected_cash || 0, period_start: range.start, period_end: range.end, expenses: exps.filter((e) => e.name && e.amount).map((e) => ({ name: e.name, amount: Number(e.amount) })), client_id: clientId });
      toast.success(t("save") + " ✓"); setExps([{ name: "", amount: "" }]); setF({ ...f, note: "" }); setClientId(crypto.randomUUID()); loadHist();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <div data-testid="handover-page">
      <PageHeader eyebrow="Bar Team → Superadmin" title={t("handover")} />
      <div className="grid lg:grid-cols-5 gap-6">
        <Bento gold className="lg:col-span-3 fade-up" testId="handover-form">
          <p className="eyebrow mb-3">{t("period")} (deposit range)</p>
          <DateFilter onChange={setRange} />
          {expected && <div className="grid grid-cols-2 gap-3 mt-4">
            <div className="rounded-xl bg-muted/60 p-3"><p className="eyebrow">{t("expectedCash")}</p><p data-testid="expected-cash" className="num font-bold text-lg text-primary">{fmtRp(expected.expected_cash)}</p><p className="text-[10px] text-muted-foreground">{expected.deposits.length} deposits · already received {fmtRp(expected.already_received)}</p></div>
            <div className="rounded-xl bg-muted/60 p-3"><p className="eyebrow">{t("difference")}</p><p data-testid="handover-diff" className={`num font-bold text-lg ${diff === 0 ? "text-emerald-500" : "text-red-500"}`}>{fmtRp(diff)}</p><p className="text-[10px] text-muted-foreground">expected − received − expenses</p></div>
          </div>}
          <div className="grid sm:grid-cols-2 gap-3 mt-4">
            <Field label={t("giver")}><Select testId="handover-giver-select" value={f.giver_id} onChange={(v) => setF({ ...f, giver_id: v })} placeholder="—" options={staff.map((s) => ({ value: s.id, label: `${s.name} (${s.role})` }))} /></Field>
            <Field label={t("receiver")}><Select testId="handover-receiver-select" value={f.receiver_id} onChange={(v) => setF({ ...f, receiver_id: v })} options={staff.filter((s) => s.role === "owner").map((s) => ({ value: s.id, label: s.name }))} /></Field>
            <Field label={t("handoverDate")}><input data-testid="handover-date-input" type="date" className="field" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></Field>
            <Field label={`${t("receivedCash")} (Rp)`}><input data-testid="handover-received-input" type="number" className="field num" value={f.received_cash} onChange={(e) => setF({ ...f, received_cash: e.target.value })} /></Field>
          </div>
          <p className="eyebrow mt-5 mb-2">{t("expenses")}</p>
          {exps.map((e, i) => (
            <div key={i} className="flex gap-2 mb-2">
              <input data-testid={`handover-exp-name-${i}`} className="field flex-1" placeholder={t("note")} value={e.name} onChange={(ev) => { const x = [...exps]; x[i] = { ...e, name: ev.target.value }; setExps(x); }} />
              <input data-testid={`handover-exp-amount-${i}`} type="number" className="field w-32 num" placeholder="Rp" value={e.amount} onChange={(ev) => { const x = [...exps]; x[i] = { ...e, amount: ev.target.value }; setExps(x); }} />
              <button onClick={() => setExps(exps.filter((_, j) => j !== i))} className="btn-ghost w-10 h-10 p-0"><Trash2 className="w-4 h-4" /></button>
            </div>))}
          <button data-testid="handover-add-expense" onClick={() => setExps([...exps, { name: "", amount: "" }])} className="text-xs font-semibold text-primary flex items-center gap-1"><Plus className="w-3 h-3" />{t("addLine")}</button>
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/60"><div><p className="eyebrow">{t("expenses")}</p><p className="num font-bold">{fmtRp(totalExp)}</p></div>
            <Field label={t("note")} className="flex-1 mx-4 hidden sm:block"><input className="field" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></Field>
            <button data-testid="handover-save-button" onClick={save} disabled={!f.giver_id || !range || busy} className="btn-primary h-11">{t("save")}</button></div>
        </Bento>
        <div className="lg:col-span-2 space-y-4">
          <Bento className="fade-up" testId="handover-history">
            <p className="eyebrow mb-3">{t("history")}</p>
            <DateFilter onChange={setHistRange} showCustom={false} />
            <div className="grid grid-cols-2 gap-3 my-4"><Stat gold label={t("receivedCash")} value={fmtRp(list.reduce((s, h) => s + h.received_cash, 0))} testId="handover-total" className="p-4" /><Stat label={t("transactions")} value={list.length} testId="handover-count" className="p-4" /></div>
            {list.map((h) => <button key={h.id} data-testid={`handover-item-${h.id}`} onClick={() => setDetail(h)} className="w-full text-left py-2.5 border-b border-border/50 text-sm hover:bg-muted/40 rounded-lg px-1"><div className="flex justify-between"><span className="font-semibold">{h.giver_name} → {h.receiver_name}</span><span className="num font-bold">{fmtRp(h.received_cash)}</span></div><p className="text-xs text-muted-foreground num">{fmtDate(h.date)} {h.time || ""} · {t("difference")} {fmtRp(h.difference)}</p></button>)}
            {!list.length && <Empty text={t("noData")} />}
          </Bento>
        </div>
      </div>
      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent data-testid="handover-detail"><DialogHeader><DialogTitle>{t("details")}</DialogTitle></DialogHeader>
          {detail && <div className="text-sm space-y-1">
            <RLine l={t("handoverDate")} r={`${fmtDate(detail.date)} ${detail.time || ""}`} /><RLine l={t("period")} r={`${detail.period_start} → ${detail.period_end}`} /><RLine l={t("giver")} r={detail.giver_name} /><RLine l={t("receiver")} r={detail.receiver_name} />
            <div className="border-t border-dashed my-2" />
            <RLine l={t("expectedCash")} r={fmtRp(detail.expected_cash)} /><RLine l={t("receivedCash")} r={fmtRp(detail.received_cash)} />
            {detail.expenses.map((e, i) => <RLine key={i} l={`− ${e.name}`} r={fmtRp(e.amount)} />)}
            <RLine bold l={t("difference")} r={fmtRp(detail.difference)} />{detail.note && <p className="text-xs text-muted-foreground pt-2">{detail.note}</p>}
          </div>}
        </DialogContent>
      </Dialog>
    </div>
  );
}
