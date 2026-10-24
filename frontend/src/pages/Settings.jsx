import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Moon, Sun, Globe, Bell, MapPin, ShieldCheck, Type, Bold } from "lucide-react";
import { api } from "../lib/api";
import { useT, LANGS } from "../lib/i18n";
import { useAuth } from "../context/AuthContext";
import { PageHeader, Bento } from "../components/common";
import { CATEGORIES } from "../components/Layout";
import { FONTS, getAppearance, setAppearance } from "../lib/appearance";
import BluetoothPrinter from "../components/BluetoothPrinter";

const Row = ({ icon: Icon, title, sub, children }) => (
  <div className="flex items-center justify-between py-4 border-b border-border/50 last:border-0 gap-4">
    <div className="flex min-w-0 items-center gap-3"><div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0"><Icon className="w-4 h-4" /></div><div className="min-w-0"><p className="text-sm font-semibold">{title}</p>{sub && <p className="text-xs text-muted-foreground">{sub}</p>}</div></div>
    <div className="shrink-0">{children}</div>
  </div>
);
const Toggle = ({ on, onChange, testId }) => <button data-testid={testId} onClick={() => onChange(!on)} className={`w-12 h-7 rounded-full transition-colors relative shrink-0 ${on ? "bg-primary" : "bg-muted"}`}><span className={`absolute left-1 top-1 w-5 h-5 rounded-full bg-white transition-transform ${on ? "translate-x-5" : "translate-x-0"}`} /></button>;

export default function Settings() {
  const { t, lang, setLang } = useT();
  const { user, setUser, theme, setTheme } = useAuth();
  const s = user.settings || {};
  const [gsUrl, setGsUrl] = useState("");
  const [ap, setAp] = useState(getAppearance());
  useEffect(() => { if (user.role !== "rider") api.get("/config").then((r) => setGsUrl(r.data.apps_script_url || "")).catch(() => {}); }, [user.role]);
  const save = async (patch) => { const { data } = await api.put("/settings", patch); setUser({ ...user, settings: data }); toast.success("Settings saved"); };
  const upd = (patch) => { const n = { ...ap, ...patch }; setAp(n); setAppearance(n); };
  const perms = (CATEGORIES[user.role] || []).flatMap((category) => category.tabs).map((item) => t(item.key));

  return (
    <div data-testid="settings-page">
      <PageHeader />
      <div className="grid lg:grid-cols-2 gap-6">
        <Bento gold className="fade-up" testId="settings-appearance">
          <p className="eyebrow mb-2">{t("appearance")}</p>
          <Row icon={theme === "dark" ? Moon : Sun} title={theme === "dark" ? t("darkMode") : t("lightMode")}>
            <div className="flex gap-1">{["dark", "light"].map((k) => <button key={k} data-testid={`theme-${k}`} onClick={() => { setTheme(k); save({ theme: k }); }} className={`h-9 px-4 rounded-full text-xs font-semibold capitalize ${theme === k ? "bg-primary text-white" : "bg-muted"}`}>{k}</button>)}</div></Row>
          <Row icon={Globe} title={t("language")} sub="ID · EN · 日本語 · 中文 · العربية">
            <select
              data-testid="language-dropdown"
              className="field w-36 h-9 text-xs"
              value={lang}
              onChange={(event) => {
                setLang(event.target.value);
                save({ language: event.target.value });
              }}
            >
              {LANGS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </Row>
          <Row icon={Bell} title={t("notifications")}><Toggle testId="notifications-toggle" on={s.notifications !== false} onChange={(v) => save({ notifications: v })} /></Row>
          {user.role === "rider" && <Row icon={MapPin} title={t("gps")} sub={t("whileUsing")}>
            <select data-testid="gps-mode-select" className="field w-40 h-9" value={s.gps_mode || "while_using"} onChange={(e) => save({ gps_mode: e.target.value })}><option value="while_using">{t("whileUsing")}</option><option value="off">Off</option></select></Row>}
          {user.role === "rider" && <Row icon={Bell} title="Motivasi kerja" sub="Ditampilkan setelah absen dan tiap tiga jam saat aplikasi terbuka">
            <select data-testid="motivation-preference-select" className="field w-40 h-9 text-xs" value={s.motivation_preference || "general"} onChange={(e) => save({ motivation_preference: e.target.value })}><option value="general">Motivasi umum</option><option value="muslim">Motivasi Muslim</option></select>
          </Row>}
        </Bento>

        <Bento className="fade-up" testId="settings-text">
          <p className="eyebrow mb-2">{t("textFont")}</p>
          <Row icon={Bold} title={t("boldText")}><Toggle testId="bold-toggle" on={ap.bold} onChange={(v) => upd({ bold: v })} /></Row>
          <Row icon={Type} title={t("fontType")}>
            <select data-testid="font-select" className="field w-44 h-9" value={ap.font} onChange={(e) => upd({ font: e.target.value })}>
              <option value="">{t("defaultFont")}</option>
              {FONTS.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
            </select>
          </Row>
        </Bento>

        <BluetoothPrinter />

        {user.role === "owner" && <Bento className="fade-up lg:col-span-2" testId="settings-permissions">
          <p className="eyebrow mb-2">{t("permissions")} · {user.role}</p>
          <Row icon={ShieldCheck} title="Modules" sub={`${perms.length} modules`} />
          <div className="flex flex-wrap gap-2 mt-3">{perms.map((p, index) => <span key={`${p}-${index}`} className="text-xs font-semibold rounded-full bg-muted px-3 py-1">{p}</span>)}</div>
          {user.role === "owner" && <div className="mt-6 pt-4 border-t border-border/50">
            <p className="eyebrow mb-2">{t("appsScript")} (Google Sheets + Drive)</p>
            <div className="flex gap-2"><input data-testid="apps-script-url-input" className="field text-xs" placeholder="https://script.google.com/macros/s/.../exec" value={gsUrl} onChange={(e) => setGsUrl(e.target.value)} />
              <button data-testid="apps-script-save" onClick={async () => { await api.put("/config", { apps_script_url: gsUrl }); toast.success(t("save") + " ✓"); }} className="btn-primary h-10 px-4 text-xs">{t("save")}</button></div>
            <p className="text-[11px] text-muted-foreground mt-2">Tutorial: /app/google-apps-script/README.md</p></div>}
        </Bento>}
      </div>
    </div>
  );
}
