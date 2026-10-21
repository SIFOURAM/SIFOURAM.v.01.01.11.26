import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { api } from "../lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon
  const [theme, setThemeState] = useState(localStorage.getItem("si4am_theme") || "dark");
  const [posUnlocked, setPosUnlocked] = useState(sessionStorage.getItem("si4am_pos") === "1");
  const inactivityTimer = useRef(null);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("si4am_theme", theme);
  }, [theme]);

  useEffect(() => {
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => setUser(false));
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
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("si4am_token"); sessionStorage.removeItem("si4am_token"); sessionStorage.removeItem("si4am_pos");
    setUser(false); setPosUnlocked(false);
  }, []);

  useEffect(() => {
    if (!user) return undefined;
    const resetTimer = () => {
      window.clearTimeout(inactivityTimer.current);
      inactivityTimer.current = window.setTimeout(logout, 10 * 60 * 1000);
    };
    const events = ["pointerdown", "keydown", "touchstart", "scroll"];
    events.forEach((event) => window.addEventListener(event, resetTimer, { passive: true }));
    resetTimer();
    return () => {
      window.clearTimeout(inactivityTimer.current);
      events.forEach((event) => window.removeEventListener(event, resetTimer));
    };
  }, [user, logout]);
  const unlockPos = () => { sessionStorage.setItem("si4am_pos", "1"); setPosUnlocked(true); };
  const setTheme = (t) => setThemeState(t);

  return <AuthCtx.Provider value={{ user, setUser, identify, login, logout, theme, setTheme, posUnlocked, unlockPos }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
