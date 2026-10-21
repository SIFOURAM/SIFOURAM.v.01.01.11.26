import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { LayoutDashboard, Boxes, Layers, ShoppingCart, Bike, Wallet, FileText, HandCoins, LineChart, BadgeDollarSign, Settings as Cog, MoreHorizontal, LogOut, Sun, Moon, Gauge, Users, Bell, UserCog, ChartNoAxesCombined, MessageCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useT } from "../lib/i18n";
import { api } from "../lib/api";
import { initials } from "../lib/helpers";
import GpsGate from "./GpsGate";
import RiderMotivation from "./RiderMotivation";

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
        <div data-testid="notif-list" className="fixed left-0 right-0 mx-auto top-20 w-[92vw] max-w-sm max-h-[70vh] overflow-y-auto bg-card text-foreground border border-border rounded-xl shadow-2xl p-3 z-50 fade-up">
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

const I = { dashboard: LayoutDashboard, inventory: Boxes, menuStock: Layers, pos: ShoppingCart, riderStock: Bike, stockRider: Bike, stockPickup: HandCoins, stockRemaining: Gauge, deposit: Wallet, invoice: FileText, riderDash: Gauge, handover: HandCoins, finance: LineChart, salary: BadgeDollarSign, settings: Cog, customers: Users, userInfo: UserCog, reports: ChartNoAxesCombined, purchaseOrders: FileText, broadcast: MessageCircle, paymentAccounts: Wallet };
const item = (to, key) => ({ to, key, icon: I[key] });

export const NAV = {
  owner: {
    main: [item("/", "dashboard"), item("/rider-stock", "riderStock"), item("/pos", "pos"), item("/inventory", "inventory")],
    more: [item("/finance", "finance")],
  },
  admin: {
    main: [item("/", "dashboard"), item("/rider-stock", "riderStock"), item("/inventory", "inventory")],
    more: [item("/settings", "settings")],
  },
  barteam: {
    main: [item("/rider-stock", "riderStock"), item("/inventory", "inventory")],
    more: [item("/settings", "settings")],
  },
  rider: {
    main: [item("/pos", "pos"), item("/rider-dashboard", "riderDash")],
    more: [item("/settings", "settings")],
  },
};
export const HOME = { owner: "/", admin: "/", barteam: "/menu-stock", rider: "/pos" };

export const CATEGORIES = {
  owner: [
    { name: "Dashboard", icon: LayoutDashboard, to: "/", tabs: [item("/", "dashboard"), item("/reports", "reports"), item("/rider-dashboard", "riderDash"), item("/salary", "salary")] },
    { name: "Stock", icon: Boxes, to: "/rider-stock", tabs: [item("/rider-stock", "riderStock"), item("/rider-stock?view=rider", "stockRider"), item("/rider-stock?view=pickup", "stockPickup"), item("/rider-stock?view=remaining", "stockRemaining"), item("/menu-stock", "menuStock")] },
    { name: "POS", icon: ShoppingCart, to: "/pos-dashboard", tabs: [item("/pos-dashboard", "posDashboard"), item("/pos", "pos"), item("/deposit", "deposit"), item("/invoice", "invoice"), item("/customers", "customers"), item("/handover", "handover")] },
    { name: "Production", icon: Layers, to: "/inventory", tabs: [item("/inventory", "inventory"), item("/menu-stock?mode=production", "menuStock"), item("/purchase-orders", "purchaseOrders")] },
    { name: "Lainnya", icon: MoreHorizontal, to: "/finance", tabs: [item("/finance", "finance"), item("/user-info", "userInfo"), item("/broadcast", "broadcast"), item("/payment-accounts", "paymentAccounts"), item("/settings", "settings")] },
  ],
  admin: [
    { name: "Dashboard", icon: LayoutDashboard, to: "/", tabs: [item("/", "dashboard"), item("/reports", "reports"), item("/rider-dashboard", "riderDash"), item("/salary", "salary")] },
    { name: "Stock", icon: Boxes, to: "/rider-stock", tabs: [item("/rider-stock", "riderStock"), item("/rider-stock?view=rider", "stockRider"), item("/rider-stock?view=pickup", "stockPickup"), item("/rider-stock?view=remaining", "stockRemaining"), item("/menu-stock", "menuStock")] },
    { name: "POS", icon: ShoppingCart, to: "/pos-dashboard", tabs: [item("/pos-dashboard", "posDashboard"), item("/deposit", "deposit")] },
    { name: "Production", icon: Layers, to: "/inventory", tabs: [item("/inventory", "inventory"), item("/menu-stock?mode=production", "menuStock"), item("/purchase-orders", "purchaseOrders")] },
    { name: "Lainnya", icon: MoreHorizontal, to: "/settings", tabs: [item("/settings", "settings")] },
  ],
  barteam: [
    { name: "Stock", icon: Boxes, to: "/rider-stock", tabs: [item("/rider-stock", "riderStock"), item("/rider-stock?view=rider", "stockRider"), item("/rider-stock?view=pickup", "stockPickup"), item("/rider-stock?view=remaining", "stockRemaining"), item("/menu-stock", "menuStock")] },
    { name: "POS", icon: ShoppingCart, to: "/deposit", tabs: [item("/deposit", "deposit")] },
    { name: "Production", icon: Layers, to: "/inventory", tabs: [item("/inventory", "inventory"), item("/menu-stock?mode=production", "menuStock"), item("/purchase-orders", "purchaseOrders")] },
    { name: "Lainnya", icon: MoreHorizontal, to: "/settings", tabs: [item("/settings", "settings")] },
  ],
  rider: [
    { name: "Dashboard", icon: Gauge, to: "/rider-dashboard", tabs: [item("/rider-dashboard", "riderDash")] },
    { name: "Stock", icon: Boxes, to: "/rider-stock?view=pickup", tabs: [item("/rider-stock?view=rider", "stockRider"), item("/rider-stock?view=pickup", "stockPickup"), item("/rider-stock?view=remaining", "stockRemaining")] },
    { name: "POS", icon: ShoppingCart, to: "/pos", tabs: [item("/pos", "pos")] },
    { name: "Lainnya", icon: MoreHorizontal, to: "/settings", tabs: [item("/settings", "settings")] },
  ],
};

function CategoryTabs({ category, t }) {
  const location = useLocation();
  const navigate = useNavigate();
  const currentPath = `${location.pathname}${location.search}`;
  return (
    <nav data-testid="category-tabs" className={`category-tab-bar ${category.name === "Lainnya" ? "category-tab-bar-more" : ""}`} aria-label={`Tab ${category.name}`}>
      <label className="category-dropdown-wrap">
        <span data-testid="category-current-label" className="category-dropdown-label">{category.name}</span>
        <select
          key={category.name}
          data-testid="category-tabs-dropdown"
          value={currentPath}
          onChange={(event) => navigate(event.target.value)}
          className="category-dropdown"
        >
          {category.tabs.map((tab) => <option key={tab.to} value={tab.to}>{t(tab.key)}</option>)}
        </select>
      </label>
    </nav>
  );
}

function useRiderGps(user) {
  const last = useRef(0);
  const [onDuty, setOnDuty] = useState(false);
  useEffect(() => {
    if (!user || user.role !== "rider") {
      setOnDuty(false);
      return undefined;
    }
    const checkDuty = () => api.get("/attendance/on-duty")
      .then((response) => setOnDuty(response.data.on_duty))
      .catch(() => setOnDuty(false));
    checkDuty();
    const interval = setInterval(checkDuty, 15000);
    return () => clearInterval(interval);
  }, [user]);
  useEffect(() => {
    if (!user || user.role !== "rider" || !onDuty || user.settings?.gps_mode === "off" || !navigator.geolocation) return;
    const id = navigator.geolocation.watchPosition((p) => {
      if (Date.now() - last.current < 30000) return;
      last.current = Date.now();
      api.post("/gps", { lat: p.coords.latitude, lng: p.coords.longitude }).catch(() => {});
    }, () => {}, { enableHighAccuracy: true });
    return () => navigator.geolocation.clearWatch(id);
  }, [user, onDuty]);
}

export default function Layout() {
  const { user, logout, theme, setTheme } = useAuth();
  const { t } = useT();
  const nav = useNavigate();
  const loc = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  useRiderGps(user);
  const { main, more } = NAV[user.role] || { main: [], more: [] };
  const roleLabel = { owner: "Owner", admin: "Admin", barteam: "Bar Team", rider: "Rider" }[user.role];
  const categories = CATEGORIES[user.role] || [];
  const activeCategory = categories.find((category) => (
    category.match
      ? category.match(loc)
      : category.tabs.some((tab) => tab.to === `${loc.pathname}${loc.search}`)
  )) || categories[0];
  useEffect(() => setMoreOpen(false), [loc.pathname, loc.search]);
  const linkCls = (isActive) => `flex items-center gap-3 px-4 h-11 rounded-xl text-sm font-medium transition-colors ${isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`;

  const Avatar = ({ size = "w-9 h-9" }) => (
    <button data-testid="nav-profile-button" onClick={() => nav("/profile")} className={`${size} rounded-full border-2 border-black overflow-hidden bg-primary text-black font-bold text-sm flex items-center justify-center shrink-0`}>
      {user.photo ? <img src={user.photo} alt="" className="w-full h-full object-cover" /> : initials(user.name)}
    </button>
  );
  const ThemeBtn = ({ id }) => <button data-testid={id} onClick={() => setTheme(theme === "dark" ? "light" : "dark")} className="p-2 rounded-lg hover:bg-muted">{theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}</button>;

  return (
    <GpsGate role={user.role}>
    <div className="min-h-screen flex">
      <aside className="hidden lg:flex flex-col w-64 xl:w-72 border-r border-border/70 p-6 sticky top-0 h-screen overflow-y-auto" data-testid="sidebar">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-2xl overflow-hidden bg-primary/10 flex items-center justify-center"><img src="/logo.png" alt="SI FOUR AM" className="w-full h-full object-contain" /></div>
          <div><p className="font-heading font-bold leading-tight">SI FOUR AM</p><p className="eyebrow">{roleLabel}</p></div>
        </div>
        <nav className="flex flex-col gap-1 flex-1">
          {categories.map((category) => {
            const CategoryIcon = category.icon;
            const selected = category.match
              ? category.match(loc)
              : category.tabs.some((tab) => tab.to === `${loc.pathname}${loc.search}`);
            return (
              <NavLink key={category.name} to={category.to} data-testid={`nav-category-${category.name.toLowerCase()}`} className={() => linkCls(selected)}>
                <CategoryIcon className="w-4 h-4" />{category.name}
              </NavLink>
            );
          })}
        </nav>
        <button data-testid="logout-button" onClick={logout} className="flex items-center gap-3 px-4 h-11 rounded-xl text-sm text-muted-foreground hover:bg-muted mt-4"><LogOut className="w-4 h-4" />{t("logout")}</button>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="flex items-center justify-between px-4 lg:px-8 h-16 sticky top-0 bg-primary text-black z-40" data-testid="top-header">
          <div className="flex items-center gap-2 lg:hidden"><img src="/assets/si-four-am-logo.png" alt="SI FOUR AM" className="w-10 h-10 object-contain" /><div><span className="font-heading font-bold">SI FOUR AM</span><p data-testid="mobile-login-role" className="text-[0.6rem] font-semibold text-black/70 leading-none">{roleLabel}</p></div></div>
          <div className="hidden lg:block"><p className="eyebrow text-black/70">{roleLabel}</p></div>
          <div className="flex items-center gap-2">
            <NotifBell />
            <ThemeBtn id="theme-toggle-button" />
            <div className="text-right hidden sm:block"><p className="text-sm font-semibold leading-tight">{user.name}</p><p className="text-[0.7rem] text-black/70">@{user.username}</p></div>
            <Avatar />
          </div>
        </header>
        {activeCategory && <CategoryTabs category={activeCategory} t={t} />}
        <main className="flex-1 max-w-[1400px] w-full mx-auto min-w-0 p-4 pb-28 lg:p-8 lg:pb-8"><Outlet /></main>
        <RiderMotivation user={user} />

        <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50 bg-background/90 backdrop-blur-xl border-t border-border/70" data-testid="bottom-nav">
          <div className="flex justify-around px-1 py-1.5 pb-[max(env(safe-area-inset-bottom),6px)]">
            {main.map((i) => (
              <NavLink key={i.to} to={i.to} end={i.to === "/"} data-testid={`bottomnav-${i.key}`}
                className={({ isActive }) => `flex flex-col items-center justify-center gap-0.5 px-1.5 py-1 rounded-xl text-[0.55rem] font-semibold min-w-0 flex-1 transition-colors ${i.key === "pos" ? "text-black" : isActive ? "text-primary" : "text-muted-foreground"}`}>
                <span className={i.key === "pos" ? "flex w-10 h-10 -mt-3 items-center justify-center rounded-full bg-primary shadow-md" : "flex items-center justify-center"}>
                  <i.icon className={i.key === "pos" ? "w-5 h-5" : "w-[0.95rem] h-[0.95rem]"} />
                </span>
                {i.key !== "pos" && <span className="truncate max-w-full">{t(i.key)}</span>}
              </NavLink>))}
            {more.length > 0 && <button data-testid="bottomnav-more" onClick={() => setMoreOpen(!moreOpen)} className={`flex flex-col items-center gap-0.5 px-1.5 py-1 text-[0.55rem] font-semibold flex-1 ${activeCategory?.name === "Lainnya" || moreOpen ? "text-primary" : "text-muted-foreground"}`}><MoreHorizontal className="w-[0.95rem] h-[0.95rem]" /><span>{t("more")}</span></button>}
          </div>
          {moreOpen && <div data-testid="more-menu" className="absolute bottom-full inset-x-2 mb-2 grid grid-cols-2 gap-1 p-2 rounded-xl border border-border bg-card shadow-2xl">{CATEGORIES[user.role].find((category) => category.name === "Lainnya")?.tabs.map((tab) => <NavLink key={tab.to} to={tab.to} data-testid={`more-${tab.key}`} className="flex items-center gap-2 h-10 px-3 rounded-lg text-sm font-semibold hover:bg-muted"><tab.icon className="w-4 h-4" />{t(tab.key)}</NavLink>)}</div>}
        </nav>
      </div>
    </div>
    </GpsGate>
  );
}
