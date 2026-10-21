import dayjs from "dayjs";
import html2canvas from "html2canvas";

export const fmtRp = (n) => "Rp " + Math.round(Number(n) || 0).toLocaleString("id-ID");
export const today = () => dayjs().format("YYYY-MM-DD");
export const fmtDate = (d) => dayjs(d).format("DD MMM YYYY");
export const fmtTime = (iso) => (iso ? dayjs(iso).format("HH:mm") : "-");

// Payroll period: 16th -> 15th
export const periodFor = (d) => {
  const x = dayjs(d);
  const start = x.date() >= 16 ? x.date(16) : x.subtract(1, "month").date(16);
  return { start: start.format("YYYY-MM-DD"), end: start.add(1, "month").date(15).format("YYYY-MM-DD") };
};

export const rangeFor = (preset, custom) => {
  const t = dayjs();
  switch (preset) {
    case "yesterday": { const y = t.subtract(1, "day").format("YYYY-MM-DD"); return { start: y, end: y }; }
    case "week": {
      const monday = t.day() === 0 ? t.subtract(6, "day") : t.subtract(t.day() - 1, "day");
      return { start: monday.format("YYYY-MM-DD"), end: t.format("YYYY-MM-DD") };
    }
    case "prevweek": {
      const monday = t.day() === 0 ? t.subtract(6, "day") : t.subtract(t.day() - 1, "day");
      return {
        start: monday.subtract(1, "week").format("YYYY-MM-DD"),
        end: monday.subtract(1, "day").format("YYYY-MM-DD"),
      };
    }
    case "month": return periodFor(t);
    case "prevmonth": return periodFor(t.subtract(1, "month"));
    case "custom": return custom;
    default: return { start: t.format("YYYY-MM-DD"), end: t.format("YYYY-MM-DD") };
  }
};

export const waNumber = (phone) => {
  let p = String(phone || "").replace(/\D/g, "");
  if (p.startsWith("0")) p = "62" + p.slice(1);
  else if (p.startsWith("8")) p = "62" + p;
  return p;
};
export const waLink = (text, phone) => `https://wa.me/${phone ? waNumber(phone) : ""}?text=${encodeURIComponent(text)}`;
export const openWA = (text, phone) => window.open(waLink(text, phone), "_blank");

export const screenshotEl = async (el, filename) => {
  if (!el) return null;
  const canvas = await html2canvas(el, { backgroundColor: null, scale: 2, useCORS: true });
  const url = canvas.toDataURL("image/png");
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  return url;
};

// Share receipt image + text via Web Share API (mobile WhatsApp), fallback to wa.me text link
export const shareReceipt = async (el, text, filename, phone) => {
  try {
    if (el && navigator.canShare) {
      const canvas = await html2canvas(el, { backgroundColor: "#111111", scale: 2, useCORS: true });
      const blob = await new Promise((r) => canvas.toBlob(r, "image/png"));
      const file = new File([blob], filename, { type: "image/png" });
      if (navigator.canShare({ files: [file] })) { await navigator.share({ files: [file], title: "SI FOUR AM", text }); return; }
    }
  } catch (e) { if (e?.name === "AbortError") return; }
  openWA(text, phone);
};

export const nowTime = () => new Date().toLocaleTimeString("id-ID", { hour12: false }).replace(/\./g, ":");

// Web Bluetooth ESC/POS thermal printing (58mm). Works on Chrome Android/desktop with BLE printers.
let btChar = null;
export const printBluetooth = async (text) => {
  if (!navigator.bluetooth) throw new Error("Web Bluetooth tidak didukung di browser ini");
  if (!btChar) {
    const dev = await navigator.bluetooth.requestDevice({ acceptAllDevices: true, optionalServices: ["000018f0-0000-1000-8000-00805f9b34fb", "e7810a71-73ae-499d-8c15-faa9aef0c3f2", "49535343-fe7d-4ae5-8fa9-9fafd205e455"] });
    const server = await dev.gatt.connect();
    const services = await server.getPrimaryServices();
    for (const s of services) { const chars = await s.getCharacteristics(); const c = chars.find((x) => x.properties.write || x.properties.writeWithoutResponse); if (c) { btChar = c; break; } }
    if (!btChar) throw new Error("Printer tidak ditemukan");
    dev.addEventListener("gattserverdisconnected", () => { btChar = null; });
  }
  const clean = text.replace(/\*/g, "").replace(/[^\x00-\x7F\n]/g, "");
  const enc = new TextEncoder();
  const bytes = new Uint8Array([0x1b, 0x40, 0x1b, 0x61, 0x00, ...enc.encode(clean + "\n\n\n\n"), 0x1d, 0x56, 0x00]);
  for (let i = 0; i < bytes.length; i += 100) await btChar.writeValue(bytes.slice(i, i + 100));
};

export const compressImage = (file, max = 640) =>
  new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const s = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = img.width * s; c.height = img.height * s;
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      resolve(c.toDataURL("image/jpeg", 0.7));
    };
    img.src = URL.createObjectURL(file);
  });

export const initials = (name = "") => name.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase();
export const roleLabel = (r) => ({
  owner: "Owner",
  admin: "Admin",
  barteam: "Bar Team",
  rider: "Rider",
}[r] || r);
