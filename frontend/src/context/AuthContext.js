import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { api } from "../lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon
  const [theme, setThemeState] = useState(localStorage.getItem("si4am_theme") || "dark");
  const [posUnlocked, setPosUnlocked] = useState(sessionStorage.getItem("si4am_pos") === "1");
  const inactivityTimer = useRef(null);
  const wibDate = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Jakarta" }).format(new Date());
  const millisToWibMidnight = () => {
    const now = new Date();
    const wib = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Jakarta" }));
    const next = new Date(wib);
    next.setHours(24, 0, 0, 0);
    return next.getTime() - wib.getTime();
  };

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("si4am_theme", theme);
  }, [theme]);

  useEffect(() => {
    const closedAt = Number(localStorage.getItem("si4am_eod_closed") || 0);
    if (closedAt && Date.now() - closedAt >= 3 * 60 * 60 * 1000) {
      localStorage.removeItem("si4am_token");
      sessionStorage.removeItem("si4am_token");
      localStorage.removeItem("si4am_eod_closed");
      setUser(false);
      return;
    }
    api.get("/auth/me").then((r) => {
      if (r.data.role !== "rider" && localStorage.getItem("si4am_session_wib_date") !== wibDate()) {
        localStorage.removeItem("si4am_token");
        sessionStorage.removeItem("si4am_token");
        setUser(false);
        return;
      }
      setUser(r.data);
    }).catch(() => setUser(false));
  }, []);

  const identify = useCallback(async (identifier, termsAccepted, privacyAccepted) => {
    const { data } = await api.post("/auth/identify", {
      identifier,
      terms_accepted: termsAccepted,
      privacy_accepted: privacyAccepted,
    });
    return data;
  }, []);

  const login = useCallback(async (accountToken, pin, remember) => {
    const { data } = await api.post("/auth/login", {
      account_token: accountToken,
      pin,
      remember,
    });
    (remember ? localStorage : sessionStorage).setItem("si4am_token", data.token);
    if (data.user.role !== "rider") localStorage.setItem("si4am_session_wib_date", wibDate());
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("si4am_token"); sessionStorage.removeItem("si4am_token"); localStorage.removeItem("si4am_eod_closed"); localStorage.removeItem("si4am_session_wib_date"); sessionStorage.removeItem("si4am_pos");
    setUser(false); setPosUnlocked(false);
  }, []);

  useEffect(() => {
    if (!user) return undefined;
    const schedule = () => {
      window.clearTimeout(inactivityTimer.current);
      if (user.role === "rider") {
        const closedAt = Number(localStorage.getItem("si4am_eod_closed") || 0);
        if (closedAt) inactivityTimer.current = window.setTimeout(logout, Math.max(0, closedAt + 3 * 60 * 60 * 1000 - Date.now()));
        return;
      }
      inactivityTimer.current = window.setTimeout(logout, millisToWibMidnight());
    };
    window.addEventListener("si4am-eod-closed", schedule);
    schedule();
    return () => {
      window.clearTimeout(inactivityTimer.current);
      window.removeEventListener("si4am-eod-closed", schedule);
    };
  }, [user, logout]);
  const unlockPos = () => { sessionStorage.setItem("si4am_pos", "1"); setPosUnlocked(true); };
  const setTheme = (t) => setThemeState(t);

  return <AuthCtx.Provider value={{ user, setUser, identify, login, logout, theme, setTheme, posUnlocked, unlockPos }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
