import { useEffect, useState } from "react";
import { Sparkles, X } from "lucide-react";
import { api } from "../lib/api";

const MUSLIM_MESSAGES = [
  {
    text: "Bekerjalah kamu, maka Allah akan melihat pekerjaanmu.",
    source: "Q.S. At-Taubah 9:105",
  },
  {
    text: "Bertebaranlah di bumi dan carilah karunia Allah.",
    source: "Q.S. Al-Jumu'ah 62:10",
  },
];

const GENERAL_MESSAGES = [
  {
    text: "The only way to do great work is to love what you do.",
    source: "Steve Jobs, Stanford Commencement Address (2005)",
  },
  {
    text: "Stay hungry. Stay foolish.",
    source: "Steve Jobs, Stanford Commencement Address (2005)",
  },
];

export default function RiderMotivation({ user }) {
  const [message, setMessage] = useState(null);
  useEffect(() => {
    if (user.role !== "rider") return undefined;
    if (user.settings?.notifications === false) return undefined;
    const key = `si4am-motivation-${user.id}`;
    const check = async () => {
      try {
        const { data } = await api.get("/attendance/on-duty");
        if (!data.on_duty) return;
        const saved = JSON.parse(localStorage.getItem(key) || "{}");
        const now = Date.now();
        if (saved.date === data.date && now - (saved.lastShown || 0) < 3 * 60 * 60 * 1000) return;
        const messages = [...MUSLIM_MESSAGES, ...GENERAL_MESSAGES];
        const item = messages[Math.floor(Math.random() * messages.length)];
        localStorage.setItem(key, JSON.stringify({ date: data.date, lastShown: now }));
        setMessage(item);
      } catch (error) {
        console.warn("Gagal memuat motivasi Rider:", error);
        setMessage(null);
      }
    };
    check();
    const timer = setInterval(check, 60000);
    return () => clearInterval(timer);
  }, [user]);

  if (!message) return null;
  return (
    <div data-testid="rider-motivation-notification" className="fixed z-[70] top-20 right-4 left-4 sm:left-auto sm:w-96 bento gold shadow-2xl">
      <button data-testid="rider-motivation-close" onClick={() => setMessage(null)} className="absolute top-3 right-3 text-muted-foreground hover:text-foreground"><X className="w-4 h-4" /></button>
      <div className="flex gap-3 pr-5"><Sparkles className="w-5 h-5 text-primary shrink-0" /><div><p className="font-heading font-bold text-sm">Semangat bertugas</p><p className="text-sm mt-1 leading-6">“{message.text}”</p><p className="text-xs text-muted-foreground mt-2">{message.source}</p></div></div>
    </div>
  );
}