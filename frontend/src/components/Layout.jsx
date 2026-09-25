import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { LayoutDashboard, Boxes, Layers, ShoppingCart, Bike, Wallet, FileText, HandCoins, LineChart, BadgeDollarSign, Settings as Cog, MoreHorizontal, LogOut, Sun, Moon, Gauge, Users, Bell, UserCog } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useT } from "../lib/i18n";
import { api } from "../lib/api";
import { initials } from "../lib/helpers";
import GpsGate from "./GpsGate";
import { getAppearance } from "../lib/appearance";

function playTriTone() {
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    const ctx = new AC();
    [[1318, 0], [1760, 0.13], [1975, 0.26]].forEach(([f, off]) => {
      const o = ctx.createOscillator(); const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination); o.type = "sine";
      const s = ctx.currentTime + off;
      o.frequency.setValueAtTime(f, s);
      g.gain.setValueAtTime(0.0001, s); g.gain.exponentialRampToValueAtTime(0.25, s + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, s + 0.15);
      o.start(s); o.stop(s + 0.17);
    });
    setTimeout(() => ctx.close(), 700);
  } catch { /* no audio */ }
}

function NotifBell() {
  const [list, setList] = useState([]);
  const [open, setOpen] = useState(false);
  const prevUnread = useRef(null);
  const load = () => api.get("/notifications").then((r) => {
    setList(r.data);
    const un = r.data.filter((n) => !n.read).length;
    if (prevUnread.current !== null && un > prevUnread.current) playTriTone();
    prevUnread.current = un;
  }).catch(() => {});
  useEffect(() => { load(); const id = setInterval(load, 20000); return () => clearInterval(id); }, []);
  const unread = list.filter((n) => !n.read).length;
  const clearAll = () => api.post("/notifications/clear").then(() => { setList([]); setOpen(false); }).catch(() => {});
  return (
    <div className="relative">
      <button data-testid="notif-bell" onClick={() => { setOpen(!open); if (unread) api.post("/notifications/read").then(load); }} className="p-2 rounded-lg hover:bg-muted relative"><Bell className="w-4 h-4" />{unread > 0 && <span data-testid="notif-count" className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">{unread}</span>}</button>
      {open && <>
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
        <div data-testid="notif-list" className="fixed left-0 right-0 mx-auto top-20 w-[92vw] max-w-sm max-h-[70vh] overflow-y-auto bento gold p-3 z-50 fade-up">
          <div className="flex items-center justify-between mb-2">
            <p className="font-heading font-bold text-sm">Notifikasi</p>
            {list.length > 0 && <button data-testid="notif-clear-all" onClick={clearAll} className="text-[11px] font-bold text-primary hover:underline">Semua Terbaca</button>}
          </div>
          <div className="space-y-1.5">
            {list.map((n) => <div key={n.id} className={`p-2 rounded-lg text-xs ${n.read ? "bg-muted/40" : "bg-primary/10"}`}><p className="font-semibold">{n.title}</p><p className="text-muted-foreground">{n.body}</p></div>)}
            {!list.length && <p className="text-xs text-muted-foreground p-4 text-center">Tidak ada notifikasi</p>}
          </div>
        </div></>}
    </div>
  );
}

const I = { dashboard: LayoutDashboard, inventory: Boxes, menuStock: Layers, pos: ShoppingCart, riderStock: Bike, deposit: Wallet, invoice: FileText, riderDash: Gauge, handover: HandCoins, finance: LineChart, salary: BadgeDollarSign, settings: Cog, customers: Users, userInfo: UserCog };
const item = (to, key) => ({ to, key, icon: I[key] });

// Bottom nav (mobile) + "More" sub-tabs. Desktop sidebar shows main + more flat.
export const NAV = {
  superadmin: { main: [item("/", "dashboard"), item("/rider-stock", "riderStock"), item("/deposit", "deposit"), item("/handover", "handover")],
    more: [item("/inventory", "inventory"), item("/menu-stock", "menuStock"), item("/pos", "pos"), item("/invoice", "invoice"), item("/rider-dashboard", "riderDash"), item("/finance", "finance"), item("/salary", "salary"), item("/customers", "customers"), item("/user-info", "userInfo"), item("/settings", "settings")] },
  barteam: { main: [item("/menu-stock", "menuStock"), item("/rider-stock", "riderStock"), item("/deposit", "deposit"), item("/inventory", "inventory"), item("/rider-dashboard", "riderDash"), item("/settings", "settings")], more: [] },
  rider: { main: [item("/pos", "pos"), item("/rider-dashboard", "riderDash"), item("/settings", "settings")], more: [] },
};
export const HOME = { superadmin: "/", barteam: "/menu-stock", rider: "/pos" };

function useRiderGps(user) {
  const last = useRef(0);
  useEffect(() => {
    if (!user || user.role !== "rider" || user.settings?.gps_mode === "off" || !navigator.geolocation) return;
    const id = navigator.geolocation.watchPosition((p) => {
      if (Date.now() - last.current < 30000) return;
      last.current = Date.now();
      api.post("/gps", { lat: p.coords.latitude, lng: p.coords.longitude }).catch(() => {});
    }, () => {}, { enableHighAccuracy: true });
    return () => navigator.geolocation.clearWatch(id);
  }, [user]);
}

export default function Layout() {
  const { user, logout, theme, setTheme } = useAuth();
  const { t } = useT();
  const nav = useNavigate();
  const loc = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  const [vm, setVm] = useState(getAppearance().view || "web");
  useEffect(() => { const h = () => setVm(getAppearance().view || "web"); window.addEventListener("appearancechange", h); return () => window.removeEventListener("appearancechange", h); }, []);
  const forceMobile = vm !== "web";
  useRiderGps(user);
  useEffect(() => setMoreOpen(false), [loc.pathname]);
  const { main, more } = NAV[user.role] || { main: [], more: [] };
  const roleLabel = { superadmin: "Superadmin", barteam: "Bar Team", rider: "Rider" }[user.role];
  const moreActive = more.some((m) => m.to === loc.pathname);
  const linkCls = (isActive) => `flex items-center gap-3 px-4 h-11 rounded-xl text-sm font-medium transition-colors ${isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`;

  const Avatar = ({ size = "w-9 h-9" }) => (
    <button data-testid="nav-profile-button" onClick={() => nav("/profile")} className={`${size} rounded-full overflow-hidden bg-primary/15 text-primary font-bold text-sm flex items-center justify-center gold shrink-0`}>
      {user.photo ? <img src={user.photo} alt="" className="w-full h-full object-cover" /> : initials(user.name)}
    </button>
  );
  const ThemeBtn = ({ id }) => <button data-testid={id} onClick={() => setTheme(theme === "dark" ? "light" : "dark")} className="p-2 rounded-lg hover:bg-muted">{theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}</button>;

  return (
    <GpsGate role={user.role}>
    <div className="min-h-screen flex">
      <aside className={`${forceMobile ? "hidden" : "hidden lg:flex"} flex-col w-64 xl:w-72 border-r border-border/70 p-6 sticky top-0 h-screen overflow-y-auto`} data-testid="sidebar">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-2xl overflow-hidden bg-primary/10 flex items-center justify-center"><img src="/logo.png" alt="SI FOUR AM" className="w-full h-full object-contain" /></div>
          <div><p className="font-heading font-bold leading-tight">SI FOUR AM</p><p className="eyebrow">{roleLabel}</p></div>
        </div>
        <nav className="flex flex-col gap-1 flex-1">
          {[...main, ...more].map((i) => (
            <NavLink key={i.to} to={i.to} end={i.to === "/"} data-testid={`nav-${i.key}`} className={({ isActive }) => linkCls(isActive)}><i.icon className="w-4 h-4" />{t(i.key)}</NavLink>
          ))}
        </nav>
        <button data-testid="logout-button" onClick={logout} className="flex items-center gap-3 px-4 h-11 rounded-xl text-sm text-muted-foreground hover:bg-muted mt-4"><LogOut className="w-4 h-4" />{t("logout")}</button>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="flex items-center justify-between px-4 lg:px-8 h-16 border-b border-border/70 sticky top-0 bg-background/80 backdrop-blur-xl z-40" data-testid="top-header">
          <div className={`items-center gap-2 ${forceMobile ? "flex" : "flex lg:hidden"}`}><img src="/logo.png" alt="SI FOUR AM" className="w-8 h-8 rounded-xl object-contain" /><span className="font-heading font-bold">SI FOUR AM</span></div>
          <div className={forceMobile ? "hidden" : "hidden lg:block"}><p className="eyebrow">{roleLabel}</p></div>
          <div className="flex items-center gap-2">
            {user.role === "superadmin" && <NotifBell />}
            <ThemeBtn id="theme-toggle-button" />
            <div className="text-right hidden sm:block"><p className="text-sm font-semibold leading-tight">{user.name}</p><p className="text-[0.7rem] text-muted-foreground">@{user.username}</p></div>
            <Avatar />
          </div>
        </header>
        <main className={`flex-1 max-w-[1400px] w-full mx-auto min-w-0 ${forceMobile ? "p-4 pb-28" : "p-4 pb-28 lg:p-8 lg:pb-8"}`}><Outlet /></main>

        {moreOpen && <div className="lg:hidden fixed inset-0 z-40 bg-black/40" onClick={() => setMoreOpen(false)} />}
        <nav className={`${forceMobile ? "" : "lg:hidden"} fixed bottom-0 inset-x-0 z-50 bg-background/90 backdrop-blur-xl border-t border-border/70`} data-testid="bottom-nav">
          {moreOpen && (
            <div className="absolute bottom-full inset-x-2 mb-2 rounded-2xl bg-card border border-border shadow-2xl p-2 grid grid-cols-2 gap-1 fade-up gold" data-testid="more-menu">
              {more.map((i) => <NavLink key={i.to} to={i.to} data-testid={`more-${i.key}`} className={({ isActive }) => `flex items-center gap-3 px-3 h-11 rounded-xl text-sm font-medium ${isActive ? "bg-primary/10 text-primary" : "hover:bg-muted"}`}><i.icon className="w-4 h-4" />{t(i.key)}</NavLink>)}
            </div>)}
          <div className="flex justify-around px-1 py-1.5 pb-[max(env(safe-area-inset-bottom),6px)]">
            {main.map((i) => (
              <NavLink key={i.to} to={i.to} end={i.to === "/"} data-testid={`bottomnav-${i.key}`}
                className={({ isActive }) => `flex flex-col items-center gap-0.5 px-1.5 py-1 rounded-xl text-[0.55rem] font-semibold min-w-0 flex-1 transition-colors ${isActive ? "text-primary" : "text-muted-foreground"}`}>
                <i.icon className="w-[0.95rem] h-[0.95rem]" /><span className="truncate w-full text-center">{t(i.key)}</span>
              </NavLink>))}
            {more.length > 0 && (
              <button data-testid="bottomnav-more" onClick={() => setMoreOpen(!moreOpen)} className={`flex flex-col items-center gap-0.5 px-1.5 py-1 text-[0.55rem] font-semibold flex-1 ${moreActive || moreOpen ? "text-primary" : "text-muted-foreground"}`}>
                <MoreHorizontal className="w-[0.95rem] h-[0.95rem]" /><span>{t("more")}</span></button>)}
          </div>
        </nav>
      </div>
    </div>
    </GpsGate>
  );
}
