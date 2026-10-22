import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { api } from "../lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon
  const [theme, setThemeState] = useState(localStorage.getItem("si4am_theme") || "dark");
  const [posUnlocked, setPosUnlocked] = useState(sessionStorage.getItem("si4am_pos") === "1");
  const sessionTimer = useRef(null);
  const clearSessionState = useCallback(() => {
    localStorage.removeItem("si4am_token");
    sessionStorage.removeItem("si4am_token");
    localStorage.removeItem("si4am_eod_closed");
    localStorage.removeItem("si4am_session_wib_date");
    sessionStorage.removeItem("si4am_pos");
    setUser(false);
    setPosUnlocked(false);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("si4am_theme", theme);
  }, [theme]);

  useEffect(() => {
    api.get("/auth/me").then((response) => setUser(response.data)).catch(() => setUser(false));
  }, []);

  useEffect(() => {
    const handleExpiredSession = () => clearSessionState();
    window.addEventListener("si4am:session-expired", handleExpiredSession);
    return () => window.removeEventListener("si4am:session-expired", handleExpiredSession);
  }, [clearSessionState]);

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
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    api.post("/auth/logout").catch(() => {});
    clearSessionState();
  }, [clearSessionState]);

  useEffect(() => {
    if (!user) return undefined;
    window.clearTimeout(sessionTimer.current);
    const sessionEnd = Date.parse(user.session_ends_at || "");
    if (Number.isFinite(sessionEnd)) {
      // setTimeout overflows (fires immediately) for delays > 2^31-1 ms (~24.8 days), e.g. Rider 30-day pre-EOD sessions
      const delay = Math.min(Math.max(0, sessionEnd - Date.now()), 2147483647);
      sessionTimer.current = window.setTimeout(() => { if (Date.now() >= sessionEnd) logout(); }, delay);
    }
    return () => {
      window.clearTimeout(sessionTimer.current);
    };
  }, [user, logout]);
  useEffect(() => {
    const updateRiderDeadline = (event) => {
      const sessionEndsAt = event.detail?.sessionEndsAt;
      if (sessionEndsAt) {
        setUser((currentUser) => currentUser ? { ...currentUser, session_ends_at: sessionEndsAt } : currentUser);
      }
    };
    window.addEventListener("si4am-eod-closed", updateRiderDeadline);
    return () => window.removeEventListener("si4am-eod-closed", updateRiderDeadline);
  }, []);
  const unlockPos = () => { sessionStorage.setItem("si4am_pos", "1"); setPosUnlocked(true); };
  const setTheme = (t) => setThemeState(t);

  return <AuthCtx.Provider value={{ user, setUser, identify, login, logout, theme, setTheme, posUnlocked, unlockPos }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
