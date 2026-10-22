import { useEffect, useRef, useState } from "react";
import { Camera, Download, MessageCircle, X, Printer } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogTitle } from "./ui/dialog";
import { compressImage, rangeFor, screenshotEl, shareReceipt, printBluetooth } from "../lib/helpers";
import { useT } from "../lib/i18n";

export const PageHeader = ({ children }) => (
  children ? <div className="flex flex-wrap gap-2 items-center justify-start mb-5 fade-up">{children}</div> : null
);

export const Bento = ({ className = "", gold, scrollable = false, children, testId, style }) => (
  <div data-testid={testId} className={`bento ${gold ? "gold" : ""} ${scrollable ? "bento-scrollable" : ""} ${className}`} style={style}>{children}</div>
);

export const Stat = ({ label, value, sub, icon: Icon, gold, testId, className = "" }) => (
  <Bento gold={gold} testId={testId} className={`fade-up ${className}`}>
    <div className="flex items-start justify-between">
      <p className="eyebrow">{label}</p>
      {Icon && <Icon className="w-4 h-4 text-primary" />}
    </div>
    <p className="mt-3 min-w-0 break-words text-[clamp(0.75rem,4vw,1.5rem)] sm:text-3xl font-bold font-heading leading-tight num tracking-tight">{value}</p>
    {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
  </Bento>
);

export const Field = ({ label, children, className = "" }) => (
  <label className={`block ${className}`}>
    {label && <span className="eyebrow block mb-1.5 whitespace-nowrap">{label}</span>}
    {children}
  </label>
);

export const Select = ({ value, onChange, options, testId, className = "", placeholder }) => (
  <select data-testid={testId} value={value ?? ""} onChange={(e) => onChange(e.target.value)} className={`field min-w-0 ${className}`}>
    {placeholder && <option value="">{placeholder}</option>}
    {options.map((o) => (typeof o === "object" ? <option key={o.value} value={o.value}>{o.label}</option> : <option key={o} value={o}>{o}</option>))}
  </select>
);

export const QtySelect = ({ value, onChange, max = 30, testId, className = "" }) => {
  const safeMax = Math.max(0, Number(max) || 0);
  const safeValue = Math.min(Math.max(0, Number(value) || 0), safeMax);

  return (
    <select
      data-testid={testId}
      value={safeValue}
      onChange={(event) => onChange(Number(event.target.value))}
      className={`qty my-0 leading-none ${className}`}
    >
      {Array.from({ length: safeMax + 1 }, (_, index) => (
        <option key={index} value={index}>
          {index}
        </option>
      ))}
    </select>
  );
};

export function DateFilter({ onChange, showCustom = true, riderPeriods = false, initialPreset = "today" }) {
  const { t } = useT();
  const [preset, setPreset] = useState(initialPreset);
  const [custom, setCustom] = useState(rangeFor(initialPreset));
  useEffect(() => {
    if (preset !== "custom") {
      const next = rangeFor(preset);
      if (custom.start !== next.start || custom.end !== next.end) setCustom(next);
      onChange(next, preset);
      return;
    }
    onChange(custom, preset);
  }, [preset, custom]); // eslint-disable-line
  const presets = riderPeriods
    ? ["today", "yesterday", "week", "prevweek", "month"]
    : ["today", "yesterday", "week", "month", "prevmonth"];
  return (
    <div className="flex flex-col gap-2 w-full min-w-0 sm:max-w-[18rem]" data-testid="date-filter">
      <select data-testid="filter-preset-select" value={preset} onChange={(e) => setPreset(e.target.value)} className="field h-[22px] w-full text-[11px] font-semibold">
        {presets.filter((p) => p !== "custom").map((p) => <option key={p} value={p}>{t(p)}</option>)}
        <option value="custom">{t("custom")}</option>
      </select>
      {(showCustom || preset === "custom") && (
        <div className="grid grid-cols-1 gap-1 sm:grid-cols-[1fr_auto_1fr] sm:items-center w-full">
          <input data-testid="filter-custom-start" type="date" className="field h-[22px] min-w-0 text-[11px] px-2" value={custom.start} onChange={(e) => { setCustom({ ...custom, start: e.target.value }); setPreset("custom"); }} />
          <span className="hidden text-center text-muted-foreground text-xs sm:block">→</span>
          <input data-testid="filter-custom-end" type="date" className="field h-[22px] min-w-0 text-[11px] px-2" value={custom.end} onChange={(e) => { setCustom({ ...custom, end: e.target.value }); setPreset("custom"); }} />
        </div>
      )}
    </div>
  );
}

export function PhotoCapture({ value, onChange, label, testId, capture = true }) {
  const ref = useRef();
  const { t } = useT();
  return (
    <div>
      <input ref={ref} type="file" accept="image/*" capture={capture ? "environment" : undefined} className="hidden" onChange={async (e) => { const f = e.target.files?.[0]; if (f) onChange(await compressImage(f)); }} />
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
  const [printing, setPrinting] = useState(false);
  useEffect(() => {
    if (open && autoShot && !shot.current) {
      shot.current = true;
      setTimeout(() => screenshotEl(ref.current, filename).catch(() => {}), 700);
    }
    if (!open) shot.current = false;
  }, [open, autoShot, filename]);
  const handleBluetoothPrint = async () => {
    if (printing) {
      return;
    }
    setPrinting(true);
    try {
      await printBluetooth(waText);
      toast.success("Struk dikirim ke printer");
    } catch (error) {
      if (error?.name !== "NotFoundError") {
        toast.error(String(error?.message || error));
      }
    } finally {
      setPrinting(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md p-0 border-0 bg-transparent shadow-none [&>button]:hidden" data-testid={testId}>
        <DialogTitle className="sr-only">{title}</DialogTitle>
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
            {navigator.bluetooth && waText && <button data-testid="receipt-print-bt" onClick={handleBluetoothPrint} disabled={printing} className="btn-ghost flex-1 disabled:cursor-not-allowed disabled:opacity-50"><Printer className="w-4 h-4" />{printing ? "Mencetak..." : "Print"}</button>}
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
