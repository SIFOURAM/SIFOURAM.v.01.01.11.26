import { useEffect, useRef, useState } from "react";
import { Sparkles, Send, X, MapPin } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";

function playChime() {
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    const ctx = new AC();
    const now = ctx.currentTime;
    const bubble = Math.random() > 0.5;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.connect(g); g.connect(ctx.destination);
    if (bubble) { o.type = "triangle"; o.frequency.setValueAtTime(480, now); o.frequency.exponentialRampToValueAtTime(220, now + 0.16); }
    else { o.type = "sine"; o.frequency.setValueAtTime(300, now); o.frequency.exponentialRampToValueAtTime(720, now + 0.12); }
    g.gain.setValueAtTime(0.0001, now);
    g.gain.exponentialRampToValueAtTime(0.2, now + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, now + 0.24);
    o.start(now); o.stop(now + 0.26);
    o.onended = () => ctx.close();
  } catch { /* audio not available */ }
}

export default function CoachChat({ hidden = false }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [pois, setPois] = useState([]);
  const [provider, setProvider] = useState(localStorage.getItem("si4am_ai_provider") || "gpt");
  const setProv = (p) => { setProvider(p); localStorage.setItem("si4am_ai_provider", p); };
  const loaded = useRef(false);
  const lastRef = useRef();

  useEffect(() => {
    if (open && !loaded.current) {
      loaded.current = true;
      api.get("/coach/history").then((r) => { setMsgs([...r.data].reverse()); if (r.data[0]?.pois) setPois(r.data[0].pois); }).catch(() => {});
    }
  }, [open]);

  // Scroll holds at the START of the last exchange (not jump fully to bottom)
  useEffect(() => { if (open && msgs.length) lastRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [msgs.length, open]);

  const send = async (q) => {
    const message = (q || text).trim();
    if (!message || busy) return;
    setText(""); setBusy(true);
    let pos = {};
    try { const p = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 5000 })); pos = { lat: p.coords.latitude, lng: p.coords.longitude }; } catch { /* no gps */ }
    try {
      const { data } = await api.post("/coach/chat", { message, provider, ...pos });
      setMsgs((m) => [...m, data]);
      setPois(data.pois || []);
      playChime();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setBusy(false); }
  };

  const quick = ["Lokasi ramai terdekat sekarang?", "Tips tembus 50 cup hari ini", "Cara nawarin bundling", "Semangatin aku dong!"];

  if (hidden) return null;

  return (
    <>
      <button data-testid="coach-open" onClick={() => setOpen(true)} aria-label="Tanya AI"
        className="fixed left-4 bottom-24 lg:bottom-20 z-40 rounded-full p-[2px] bg-[linear-gradient(135deg,#0064e0,#8a2be2,#ff4d9d,#FF6B00)] shadow-xl hover:scale-105 active:scale-95 transition-transform">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[linear-gradient(135deg,#0064e0,#8a2be2,#ff4d9d,#FF6B00)]">
          <Sparkles className="w-4 h-4 text-white" />
        </span>
      </button>

      {open && (
        <div className="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center sm:p-4" onClick={() => setOpen(false)}>
          <div onClick={(e) => e.stopPropagation()} data-testid="coach-panel"
            className="w-full sm:max-w-md h-[88vh] sm:h-[620px] flex flex-col overflow-hidden rounded-t-3xl sm:rounded-3xl bg-card border border-border/60 shadow-2xl">
            <div className="flex items-center gap-3 p-4 border-b border-border/60 bg-gradient-to-r from-primary/10 to-transparent">
              <div className="w-9 h-9 rounded-full bg-[linear-gradient(135deg,#0064e0,#8a2be2,#ff4d9d,#FF6B00)] flex items-center justify-center shrink-0"><Sparkles className="w-4 h-4 text-white" /></div>
              <div className="flex-1 min-w-0"><p className="font-heading font-bold leading-tight">SI FOUR AM AI</p><p className="text-[11px] text-muted-foreground truncate">Tanya apa saja — dimaksimalkan untuk jualan ☕</p></div>
              <select data-testid="coach-provider" value={provider} onChange={(e) => setProv(e.target.value)} className="text-[11px] font-semibold rounded-full bg-muted px-2 py-1 border border-border shrink-0">
                <option value="gpt">GPT</option><option value="claude">Claude</option><option value="gemini">Gemini</option>
              </select>
              <button data-testid="coach-close" onClick={() => setOpen(false)} className="p-2 rounded-full hover:bg-muted"><X className="w-4 h-4" /></button>
            </div>

            {pois.length > 0 && (
              <div className="flex gap-1 overflow-x-auto no-scrollbar px-3 py-2 border-b border-border/40">
                {pois.slice(0, 8).map((p, i) => <a key={i} href={`https://www.google.com/maps?q=${p.lat},${p.lng}`} target="_blank" rel="noreferrer" className="shrink-0 text-[10px] rounded-full bg-muted px-2 py-1 flex items-center gap-1"><MapPin className="w-3 h-3 text-primary" />{p.name}</a>)}
              </div>
            )}

            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm bg-muted/20">
              {!msgs.length && <div className="text-center text-muted-foreground text-xs pt-10">Halo! 👋 Aku asisten AI SI FOUR AM.<br />Tanya <b>apa saja</b> — lokasi ramai, tips jualan, atau hal lain. Ketik di bawah atau pilih cepat.</div>}
              {msgs.map((m, idx) => (
                <div key={m.id || idx} ref={idx === msgs.length - 1 ? lastRef : null} className="space-y-2 chat-pop">
                  {m.message && <div data-testid="chat-user" className="ml-auto max-w-[82%] w-fit rounded-2xl rounded-br-sm bg-primary text-white px-3.5 py-2 shadow-sm whitespace-pre-wrap">{m.message}</div>}
                  <div className="flex items-end gap-2 max-w-[90%]">
                    <div className="w-6 h-6 rounded-full bg-[linear-gradient(135deg,#0064e0,#8a2be2,#ff4d9d,#FF6B00)] flex items-center justify-center shrink-0 mb-0.5"><Sparkles className="w-3 h-3 text-white" /></div>
                    <div data-testid="chat-ai" className="rounded-2xl rounded-bl-sm bg-card border border-border/60 px-3.5 py-2 whitespace-pre-wrap leading-relaxed shadow-sm">{m.reply}</div>
                  </div>
                </div>))}
              {busy && (
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-[linear-gradient(135deg,#0064e0,#8a2be2,#ff4d9d,#FF6B00)] flex items-center justify-center"><Sparkles className="w-3 h-3 text-white" /></div>
                  <div className="rounded-2xl rounded-bl-sm bg-card border border-border/60 px-4 py-3 flex gap-1"><span className="chat-dot" /><span className="chat-dot" style={{ animationDelay: ".15s" }} /><span className="chat-dot" style={{ animationDelay: ".3s" }} /></div>
                </div>)}
            </div>

            <div className="p-3 border-t border-border/60 bg-card">
              <div className="flex gap-1 overflow-x-auto no-scrollbar pb-2">{quick.map((q) => <button key={q} data-testid="coach-quick" onClick={() => send(q)} className="shrink-0 text-[11px] rounded-full border border-border px-3 py-1 hover:bg-muted">{q}</button>)}</div>
              <div className="flex gap-2 items-center">
                <input data-testid="coach-input" className="field rounded-full" placeholder="Tanya apa saja…" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} />
                <button data-testid="coach-send" disabled={busy} onClick={() => send()} className="btn-primary w-11 h-10 p-0 rounded-full shrink-0"><Send className="w-4 h-4" /></button>
              </div>
            </div>
          </div>
        </div>)}
    </>
  );
}
