import "@/App.css";
import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { RotateCcw } from "lucide-react";
import { Toaster } from "./components/ui/sonner";
import { applyAppearance, getAppearance } from "./lib/appearance";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { api } from "./lib/api";
import { LangProvider } from "./lib/i18n";
import Layout, { HOME } from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Inventory from "./pages/Inventory";
import MenuStock from "./pages/MenuStock";
import POS from "./pages/POS";
import POSDashboard from "./pages/POSDashboard";
import RiderStock from "./pages/RiderStock";
import Deposit from "./pages/DepositPage";
import Invoice from "./pages/Invoice";
import RiderDashboard from "./pages/RiderDashboard";
import Handover from "./pages/CashHandover";
import Finance from "./pages/Finance";
import Salary from "./pages/Salary";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import Customers from "./pages/Customers";
import UserInfo from "./pages/UserInfo";
import Reports from "./pages/Reports";
import PurchaseOrders from "./pages/PurchaseOrders";
import { Broadcast, PaymentAccounts } from "./pages/MoreTools";

const S = ["owner"];
const SB = ["owner", "admin", "barteam"];
const ALL = ["owner", "admin", "barteam", "rider"];
const REPORT_ACCESS = ["owner", "admin"];
const POS_ACCESS = ["owner", "rider"];

function Guard({ allow, children }) {
  const { user } = useAuth();
  if (!allow.includes(user.role)) return <Navigate to={HOME[user.role]} replace />;
  return children;
}

function Home() {
  const { user } = useAuth();
  if (!["owner", "admin"].includes(user.role)) return <Navigate to={HOME[user.role]} replace />;
  return <Dashboard />;
}

function Shell() {
  const { user } = useAuth();
  if (user === null) return <div className="min-h-screen flex items-center justify-center"><img src="/assets/si-four-am-logo.png" alt="Memuat SI FOUR AM" className="w-24 h-24 object-contain si4am-loader" /></div>;
  if (!user) return <Routes><Route path="*" element={<Login />} /></Routes>;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/inventory" element={<Guard allow={SB}><Inventory /></Guard>} />
        <Route path="/menu-stock" element={<Guard allow={SB}><MenuStock /></Guard>} />
        <Route path="/purchase-orders" element={<Guard allow={SB}><PurchaseOrders /></Guard>} />
        <Route path="/pos" element={<Guard allow={POS_ACCESS}><POS /></Guard>} />
        <Route path="/pos-dashboard" element={<Guard allow={REPORT_ACCESS}><POSDashboard /></Guard>} />
        <Route path="/rider-stock" element={<Guard allow={ALL}><RiderStock /></Guard>} />
        <Route path="/deposit" element={<Guard allow={SB}><Deposit /></Guard>} />
        <Route path="/invoice" element={<Guard allow={S}><Invoice /></Guard>} />
        <Route path="/rider-dashboard" element={<Guard allow={ALL}><RiderDashboard /></Guard>} />
        <Route path="/handover" element={<Guard allow={S}><Handover /></Guard>} />
        <Route path="/finance" element={<Guard allow={S}><Finance /></Guard>} />
        <Route path="/reports" element={<Guard allow={REPORT_ACCESS}><Reports /></Guard>} />
        <Route path="/salary" element={<Guard allow={ALL}><Salary /></Guard>} />
        <Route path="/customers" element={<Guard allow={SB}><Customers /></Guard>} />
        <Route path="/user-info" element={<Guard allow={S}><UserInfo /></Guard>} />
        <Route path="/broadcast" element={<Guard allow={S}><Broadcast /></Guard>} />
        <Route path="/payment-accounts" element={<Guard allow={S}><PaymentAccounts /></Guard>} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

function LiveShell() {
  const { user, setUser } = useAuth();
  const [revision, setRevision] = useState(0);
  const knownRevision = useRef(null);

  useEffect(() => {
    if (!user) {
      return undefined;
    }
    const sync = async () => {
      try {
        const { data } = await api.get("/sync/revision");
        if (data.session_ends_at && data.session_ends_at !== user.session_ends_at) {
          setUser((currentUser) => currentUser ? { ...currentUser, session_ends_at: data.session_ends_at } : currentUser);
        }
        if (knownRevision.current === null) {
          knownRevision.current = data.revision;
        } else if (knownRevision.current !== data.revision) {
          knownRevision.current = data.revision;
          setRevision((currentRevision) => currentRevision + 1);
        }
      } catch {}
    };
    const handleLocalChange = () => setRevision((currentRevision) => currentRevision + 1);
    sync();
    const intervalId = window.setInterval(sync, 6000);
    window.addEventListener("si4am:data-changed", handleLocalChange);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("si4am:data-changed", handleLocalChange);
    };
  }, [user, setUser]);

  return <Shell key={revision} />;
}

export default function App() {
  useEffect(() => { applyAppearance(getAppearance()); }, []);
  return (
    <LangProvider>
      <AuthProvider>
        <BrowserRouter><LiveShell /></BrowserRouter>
        <Toaster position="top-right" richColors />
        <div className="rotate-lock" data-testid="rotate-lock">
          <RotateCcw className="w-12 h-12 text-primary" />
          <p style={{ fontFamily: "Outfit", fontWeight: 800, fontSize: 20 }}>Putar ke Mode Portrait</p>
          <p style={{ opacity: 0.7, fontSize: 13 }}>Aplikasi SI FOUR AM hanya dapat digunakan dalam posisi tegak (portrait). Silakan putar perangkat Anda.</p>
        </div>
      </AuthProvider>
    </LangProvider>
  );
}
