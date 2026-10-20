import { useCallback, useEffect, useState } from "react";
import { MapPin } from "lucide-react";

// Riders must grant location permission before using the app
export default function GpsGate({ role, children }) {
  const [ok, setOk] = useState(role !== "rider" ? true : null);
  const ask = useCallback(() => {
    navigator.geolocation.getCurrentPosition(
      () => setOk(true),
      () => setOk(false),
      { timeout: 10000 },
    );
  }, []);
  useEffect(() => {
    if (role !== "rider") return;
    if (!navigator.geolocation) return setOk(false);
    if (navigator.permissions?.query) navigator.permissions.query({ name: "geolocation" }).then((p) => { if (p.state === "granted") setOk(true); else ask(); p.onchange = () => setOk(p.state === "granted"); }).catch(ask);
    else ask();
  }, [ask, role]);
  if (ok) return children;
  return (
    <div className="min-h-screen flex items-center justify-center p-6" data-testid="gps-gate">
      <div className="bento gold max-w-sm text-center fade-up">
        <div className="w-16 h-16 rounded-2xl bg-primary/15 text-primary flex items-center justify-center mx-auto mb-4"><MapPin className="w-8 h-8" /></div>
        <h2 className="text-2xl font-bold mb-2">Aktifkan Lokasi</h2>
        <p className="text-sm text-muted-foreground mb-6">Aplikasi kasir wajib mengakses GPS ("Izinkan Saat Aplikasi Digunakan") agar Owner bisa memantau rider dan Coach AI bisa merekomendasikan lokasi ramai terdekat.</p>
        {ok === false && <p className="text-xs text-red-500 mb-3">Izin lokasi ditolak. Buka pengaturan browser → Izin situs → Lokasi → Izinkan, lalu coba lagi.</p>}
        <button data-testid="gps-enable-button" onClick={ask} className="btn-primary w-full">Izinkan Lokasi</button>
      </div>
    </div>
  );
}
