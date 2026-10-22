import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "./AuthContext";

const LiveDataContext = createContext(0);

export function LiveDataProvider({ children }) {
  const { user, setUser } = useAuth();
  const [revision, setRevision] = useState(0);
  const knownRevision = useRef(null);

  const refreshRevision = useCallback(() => {
    setRevision((currentRevision) => currentRevision + 1);
  }, []);

  useEffect(() => {
    if (!user) {
      knownRevision.current = null;
      return undefined;
    }
    const sync = async () => {
      try {
        const { data } = await api.get("/sync/revision");
        if (data.session_ends_at && data.session_ends_at !== user.session_ends_at) {
          setUser((currentUser) => (
            currentUser ? { ...currentUser, session_ends_at: data.session_ends_at } : currentUser
          ));
        }
        if (knownRevision.current === null) {
          knownRevision.current = data.revision;
        } else if (knownRevision.current !== data.revision) {
          knownRevision.current = data.revision;
          refreshRevision();
        }
      } catch {}
    };
    sync();
    const intervalId = window.setInterval(sync, 6000);
    window.addEventListener("si4am:data-changed", refreshRevision);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("si4am:data-changed", refreshRevision);
    };
  }, [refreshRevision, setUser, user]);

  return <LiveDataContext.Provider value={revision}>{children}</LiveDataContext.Provider>;
}

export const useLiveRevision = () => useContext(LiveDataContext);