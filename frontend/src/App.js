import "@/App.css";
import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { RotateCcw } from "lucide-react";
import { Toaster } from "./components/ui/sonner";
import { applyAppearance, getAppearance } from "./lib/appearance";
import { AuthProvider, useAuth } from "./context/AuthContext";
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
        <Route path="/salary" element={<Guard allow={SB}><Salary /></Guard>} />
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

export default function App() {
  useEffect(() => { applyAppearance(getAppearance()); }, []);
  return (
    <LangProvider>
      <AuthProvider>
        <BrowserRouter><Shell /></BrowserRouter>
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
