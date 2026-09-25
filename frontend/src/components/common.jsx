import { useEffect, useRef, useState } from "react";
import { Camera, Download, MessageCircle, X, Printer } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent } from "./ui/dialog";
import { compressImage, rangeFor, screenshotEl, shareReceipt, printBluetooth } from "../lib/helpers";
import { useT } from "../lib/i18n";

export const PageHeader = ({ children }) => (
  children ? <div className="flex flex-wrap gap-2 items-center justify-end mb-5 fade-up">{children}</div> : null
);

export const Bento = ({ className = "", gold, children, testId, style }) => (
  <div data-testid={testId} className={`bento ${gold ? "gold" : ""} ${className}`} style={style}>{children}</div>
);

export const Stat = ({ label, value, sub, icon: Icon, gold, testId, className = "" }) => (
  <Bento gold={gold} testId={testId} className={`fade-up ${className}`}>
    <div className="flex items-start justify-between">
      <p className="eyebrow">{label}</p>
      {Icon && <Icon className="w-4 h-4 text-primary" />}
    </div>
    <p className="mt-3 text-2xl sm:text-3xl font-bold font-heading num tracking-tight">{value}</p>
    {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
  </Bento>
);

export const Field = ({ label, children, className = "" }) => (
  <label className={`block ${className}`}>
    {label && <span className="eyebrow block mb-1.5">{label}</span>}
    {children}
  </label>
);

export const Select = ({ value, onChange, options, testId, className = "", placeholder }) => (
  <select data-testid={testId} value={value ?? ""} onChange={(e) => onChange(e.target.value)} className={`field ${className}`}>
    {placeholder && <option value="">{placeholder}</option>}
    {options.map((o) => (typeof o === "object" ? <option key={o.value} value={o.value}>{o.label}</option> : <option key={o} value={o}>{o}</option>))}
  </select>
);

export const QtySelect = ({ value, onChange, max = 30, testId, className = "" }) => (
  <select data-testid={testId} value={value} onChange={(e) => onChange(Number(e.target.value))} className={`qty ${className}`}>
    {Array.from({ length: max + 1 }, (_, i) => <option key={i} value={i}>{i}</option>)}
  </select>
);

export function DateFilter({ onChange, showCustom = true }) {
  const { t } = useT();
  const [preset, setPreset] = useState("today");
  const [custom, setCustom] = useState(rangeFor("today"));
  useEffect(() => { onChange(rangeFor(preset, custom), preset); }, [preset, custom]); // eslint-disable-line
  const presets = ["today", "yesterday", "week", "month", "prevmonth"];
  return (
    <div className="flex flex-col gap-2 w-full sm:w-auto" data-testid="date-filter">
      <select data-testid="filter-preset-select" value={preset} onChange={(e) => setPreset(e.target.value)} className="field h-9 w-full sm:w-52 text-xs font-semibold">
        {presets.filter((p) => p !== "custom").map((p) => <option key={p} value={p}>{t(p)}</option>)}
        <option value="custom">{t("custom")}</option>
      </select>
      {(showCustom || preset === "custom") && (
        <div className="flex gap-1 items-center">
          <input data-testid="filter-custom-start" type="date" className="field h-9 flex-1 text-xs px-2" value={custom.start} onChange={(e) => { setCustom({ ...custom, start: e.target.value }); setPreset("custom"); }} />
          <span className="text-muted-foreground text-xs">→</span>
          <input data-testid="filter-custom-end" type="date" className="field h-9 flex-1 text-xs px-2" value={custom.end} onChange={(e) => { setCustom({ ...custom, end: e.target.value }); setPreset("custom"); }} />
        </div>
      )}
    </div>
  );
}

export function PhotoCapture({ value, onChange, label, testId }) {
  const ref = useRef();
  const { t } = useT();
  return (
    <div>
      <input ref={ref} type="file" accept="image/*" capture="environment" className="hidden" onChange={async (e) => { const f = e.target.files?.[0]; if (f) onChange(await compressImage(f)); }} />
      <button type="button" data-testid={testId} onClick={() => ref.current.click()}
        className="w-full aspect-video rounded-2xl border-2 border-dashed border-border hover:border-primary/60 transition-colors flex items-center justify-center overflow-hidden bg-muted/40">
        {value ? <img src={value} alt="captured" className="w-full h-full object-cover" /> : <span className="flex items-center gap-2 text-sm text-muted-foreground"><Camera className="w-5 h-5" />{label || t("takePhoto")}</span>}
      </button>
    </div>
  );
}

// Receipt popup: auto-screenshot on open, download, WhatsApp
export function ReceiptModal({ open, onClose, title, waText, waPhone, filename = "receipt.png", autoShot = true, children, testId = "receipt-modal" }) {
  const ref = useRef();
  const shot = useRef(false);
  useEffect(() => {
    if (open && autoShot && !shot.current) {
      shot.current = true;
      setTimeout(() => screenshotEl(ref.current, filename).catch(() => {}), 700);
    }
    if (!open) shot.current = false;
  }, [open, autoShot, filename]);
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md p-0 border-0 bg-transparent shadow-none [&>button]:hidden" data-testid={testId}>
        <div className="relative">
          <button onClick={onClose} data-testid="receipt-close" className="absolute -top-3 -right-3 z-10 w-8 h-8 rounded-full bg-card border border-border flex items-center justify-center"><X className="w-4 h-4" /></button>
          <div ref={ref} className="rounded-3xl bg-white text-black p-6 gold" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            <div className="text-center mb-4">
              <img src="/logo.png" alt="SI FOUR AM" className="mx-auto w-14 h-14 object-contain" />
              <p className="font-black text-lg mt-2 tracking-tight" style={{ fontFamily: "Outfit" }}>SI FOUR AM</p>
              <p className="text-[11px] uppercase tracking-widest text-gray-500">{title}</p>
            </div>
            <div className="border-t border-dashed border-gray-300 my-3" />
            {children}
          </div>
          <div className="flex gap-2 mt-4">
            <button data-testid="receipt-download" onClick={() => screenshotEl(ref.current, filename)} className="btn-ghost flex-1"><Download className="w-4 h-4" />PNG</button>
            {navigator.bluetooth && waText && <button data-testid="receipt-print-bt" onClick={() => printBluetooth(waText).catch((e) => toast.error(String(e.message || e)))} className="btn-ghost flex-1"><Printer className="w-4 h-4" />Print</button>}
            {waText && <button data-testid="receipt-whatsapp" onClick={() => shareReceipt(ref.current, waText, filename, waPhone)} className="btn-wa flex-1"><MessageCircle className="w-4 h-4" />WhatsApp</button>}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export const RLine = ({ l, r, bold }) => (
  <div className={`flex justify-between text-xs py-0.5 ${bold ? "font-bold text-sm" : ""}`}><span className="text-gray-600">{l}</span><span className="num">{r}</span></div>
);

export const Empty = ({ text }) => <div className="text-center text-sm text-muted-foreground py-12" data-testid="empty-state">{text}</div>;
