import axios from "axios";

export const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

let sessionExpirySent = false;

api.interceptors.response.use(
  (response) => {
    const method = response.config?.method?.toLowerCase();
    const url = response.config?.url || "";
    const ignoredRealtimePaths = ["/gps", "/notifications/read"];
    const skipsRealtime = ignoredRealtimePaths.some((path) => url.startsWith(path));
    if (["post", "put", "delete"].includes(method) && !url.startsWith("/auth/") && !skipsRealtime) {
      window.dispatchEvent(new Event("si4am:data-changed"));
    }
    return response;
  },
  (error) => {
    const isUnauthorized = error.response?.status === 401;
    const url = error.config?.url || "";
    const isAuthRequest = url.startsWith("/auth/");
    if (isUnauthorized && !isAuthRequest && !sessionExpirySent) {
      sessionExpirySent = true;
      window.dispatchEvent(new Event("si4am:session-expired"));
      window.setTimeout(() => {
        sessionExpirySent = false;
      }, 1000);
    }
    return Promise.reject(error);
  },
);

export const errMsg = (e) => {
  const d = e?.response?.data?.detail;
  if (!d) return e?.message || "Something went wrong";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join(" ");
  return d.msg || String(d);
};
