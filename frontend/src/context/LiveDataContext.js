import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "./AuthContext";

const LiveDataContext = createContext(0);

export function LiveDataProvider({ children }) {
  const { user, setUser } = useAuth();
  const [revision, setRevision] = useState(0);
  const knownRevision = useRef(null);
  const localRefreshPending = useRef(false);
  const userRef = useRef(user);
  const userId = user?.id;

  useEffect(() => {
    userRef.current = user;
  }, [user]);

  const refreshRevision = useCallback(() => {
    setRevision((currentRevision) => currentRevision + 1);
  }, []);

  useEffect(() => {
    if (!userId) {
      knownRevision.current = null;
      return undefined;
    }
    const sync = async () => {
      try {
        const { data } = await api.get("/sync/revision");
        if (data.session_ends_at && data.session_ends_at !== userRef.current?.session_ends_at) {
          setUser((currentUser) => (
            currentUser ? { ...currentUser, session_ends_at: data.session_ends_at } : currentUser
          ));
        }
        if (knownRevision.current === null) {
          knownRevision.current = data.revision;
        } else if (knownRevision.current !== data.revision) {
          knownRevision.current = data.revision;
          if (localRefreshPending.current) {
            localRefreshPending.current = false;
          } else {
            refreshRevision();
          }
        }
      } catch (error) {
        console.warn("Gagal menyinkronkan revision data:", error);
      }
    };
    sync();
    const intervalId = window.setInterval(sync, 6000);
    const handleLocalChange = () => {
      localRefreshPending.current = true;
      refreshRevision();
    };
    window.addEventListener("si4am:data-changed", handleLocalChange);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("si4am:data-changed", handleLocalChange);
    };
  }, [refreshRevision, setUser, userId]);

  return <LiveDataContext.Provider value={revision}>{children}</LiveDataContext.Provider>;
}

export const useLiveRevision = () => useContext(LiveDataContext);