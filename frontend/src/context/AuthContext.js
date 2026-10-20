import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon
  const [theme, setThemeState] = useState(localStorage.getItem("si4am_theme") || "dark");
  const [posUnlocked, setPosUnlocked] = useState(sessionStorage.getItem("si4am_pos") === "1");

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

  const logout = () => {
    localStorage.removeItem("si4am_token"); sessionStorage.removeItem("si4am_token"); sessionStorage.removeItem("si4am_pos");
    setUser(false); setPosUnlocked(false);
  };
  const unlockPos = () => { sessionStorage.setItem("si4am_pos", "1"); setPosUnlocked(true); };
  const setTheme = (t) => setThemeState(t);

  return <AuthCtx.Provider value={{ user, setUser, identify, login, logout, theme, setTheme, posUnlocked, unlockPos }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
