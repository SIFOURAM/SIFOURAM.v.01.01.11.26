import { useRef, useState } from "react";
import { toast } from "sonner";
import { ArrowLeft, Check, ChevronDown, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { LANGS, useT } from "../lib/i18n";
import { errMsg } from "../lib/api";

const DOCUMENTS = {
  terms: {
    title: "Syarat & Ketentuan",
    body: [
      "Aplikasi SI FOUR AM digunakan untuk operasional bisnis yang sah dan terotorisasi.",
      "Setiap pengguna wajib menjaga kerahasiaan PIN, menggunakan akun pribadi, dan mencatat transaksi secara benar.",
      "Owner dapat menonaktifkan akses apabila terdapat pelanggaran kebijakan operasional.",
    ],
  },
  privacy: {
    title: "Kebijakan Privasi",
    body: [
      "SI FOUR AM menyimpan identitas akun, data operasional, lokasi kerja saat rider bertugas, dan bukti foto.",
      "Data hanya digunakan untuk operasional, laporan, keamanan, serta pengelolaan bisnis SI FOUR AM.",
      "Akses data dibatasi berdasarkan role. Data tidak dibagikan untuk kebutuhan yang tidak terkait operasional.",
    ],
  },
};

function DocumentModal({ type, onClose, onAgree }) {
  const [atBottom, setAtBottom] = useState(false);
  const doc = DOCUMENTS[type];
  const trackScroll = (event) => {
    const { scrollHeight, scrollTop, clientHeight } = event.currentTarget;
    setAtBottom(scrollTop + clientHeight >= scrollHeight - 4);
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/70 p-4 flex items-end sm:items-center justify-center">
      <section className="w-full max-w-lg bg-card text-foreground rounded-2xl overflow-hidden shadow-2xl">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <p className="eyebrow">SI FOUR AM</p>
            <h2 className="font-heading text-xl font-bold">{doc.title}</h2>
          </div>
          <button data-testid="auth-document-close" onClick={onClose} className="btn-ghost w-9 h-9 p-0">
            <ArrowLeft className="w-4 h-4" />
          </button>
        </div>
        <div
          data-testid={`auth-${type}-document`}
          onScroll={trackScroll}
          className="h-64 overflow-y-auto p-5 space-y-5 text-sm leading-7"
        >
          {doc.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          <div className="h-32 flex items-end text-xs text-muted-foreground">
            Akhir dokumen · versi 2026-06-01
          </div>
        </div>
        <div className="p-4 border-t border-border">
          <button
            data-testid={`auth-${type}-agree`}
            disabled={!atBottom}
            onClick={() => onAgree(type)}
            className="auth-gold-button w-full"
          >
            <Check className="w-4 h-4" /> Saya sudah membaca dan menyetujui
          </button>
        </div>
      </section>
    </div>
  );
}

export default function Login() {
  const { identify, login } = useAuth();
  const { lang, setLang } = useT();
  const [identifier, setIdentifier] = useState("");
  const [stage, setStage] = useState("identity");
  const [account, setAccount] = useState(null);
  const [digits, setDigits] = useState(Array(6).fill(""));
  const [consent, setConsent] = useState({ terms: false, privacy: false });
  const [document, setDocument] = useState(null);
  const [busy, setBusy] = useState(false);
  const pinRefs = useRef([]);

  const handleIdentify = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const data = await identify(identifier, consent.terms, consent.privacy);
      setAccount(data);
      setStage("pin");
      setTimeout(() => pinRefs.current[0]?.focus(), 100);
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy(false);
    }
  };

  const handlePin = async (event) => {
    event.preventDefault();
    const pin = digits.join("");
    if (pin.length !== 6) return;
    setBusy(true);
    try {
      const user = await login(account.account_token, pin, true);
      toast.success(`Selamat datang, ${user.name}`);
    } catch (error) {
      toast.error(errMsg(error));
      setDigits(Array(6).fill(""));
      pinRefs.current[0]?.focus();
    } finally {
      setBusy(false);
    }
  };

  const updateDigit = (index, value) => {
    const clean = value.replace(/\D/g, "");
    if (clean.length > 1) {
      const next = Array(6).fill("");
      clean.slice(0, 6).split("").forEach((digit, itemIndex) => {
        next[itemIndex] = digit;
      });
      setDigits(next);
      pinRefs.current[Math.min(clean.length, 6) - 1]?.focus();
      return;
    }
    const next = [...digits];
    next[index] = clean;
    setDigits(next);
    if (clean && index < 5) pinRefs.current[index + 1]?.focus();
  };

  const handleKeyDown = (index, event) => {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      pinRefs.current[index - 1]?.focus();
    }
  };

  return (
    <div className="auth-page" data-testid="login-page">
      <main className="auth-panel fade-up">
        <div className="flex items-center justify-between gap-4">
          <img src="/assets/si-four-am-logo.png" alt="SI FOUR AM" className="w-20 h-20 object-contain" />
          <label className="relative">
            <span className="sr-only">Bahasa</span>
            <select
              data-testid="login-language-dropdown"
              value={lang}
              onChange={(event) => setLang(event.target.value)}
              className="field h-10 w-32 appearance-none pr-8 text-xs"
            >
              {LANGS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
            <ChevronDown className="w-4 h-4 absolute right-2.5 top-3 pointer-events-none" />
          </label>
        </div>
        <div className="mt-8 mb-8">
          <p className="eyebrow">Coffee Cart Operating System</p>
          <h1 className="font-heading text-4xl font-bold mt-2">SI FOUR AM{stage === "pin" ? " APP" : ""}</h1>
          <p className="text-sm text-muted-foreground mt-2">
            {stage === "pin" ? "Masuk PIN Anda." : "Masuk ke akun Anda."}
          </p>
        </div>
        {stage === "identity" ? (
          <form onSubmit={handleIdentify} className="space-y-5">
            <label className="block">
              <span className="eyebrow block mb-2">Email, username, atau nomor WhatsApp</span>
              <input
                data-testid="login-identifier-input"
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                className="field h-12"
                autoComplete="username"
                inputMode="email"
                required
              />
            </label>
            <ConsentLinks consent={consent} setDocument={setDocument} />
            <button
              data-testid="login-continue-button"
              disabled={busy || !consent.terms || !consent.privacy || !identifier.trim()}
              className="auth-gold-button w-full"
            >
              {busy ? "Memeriksa..." : "Lanjut"}
            </button>
          </form>
        ) : (
          <form onSubmit={handlePin} className="space-y-6">
            <div>
              <div className="flex gap-2 justify-between" data-testid="pin-inputs">
                {digits.map((digit, index) => (
                  <input
                    key={index}
                    ref={(element) => { pinRefs.current[index] = element; }}
                    data-testid={`pin-digit-${index}`}
                    type="tel"
                    inputMode="numeric"
                    autoComplete={index === 0 ? "one-time-code" : "off"}
                    maxLength={6}
                    value={digit}
                    onChange={(event) => updateDigit(index, event.target.value)}
                    onKeyDown={(event) => handleKeyDown(index, event)}
                    className={`pin-box ${digit ? "pin-box-filled" : ""}`}
                    aria-label={`Digit PIN ${index + 1}`}
                  />
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-3">Akun: {account?.user?.name}</p>
            </div>
            <ConsentLinks consent={consent} setDocument={setDocument} />
            <button
              data-testid="pin-continue-button"
              disabled={busy || digits.join("").length !== 6}
              className="auth-gold-button w-full"
            >
              {busy ? "Memeriksa..." : "Lanjut"}
            </button>
            <button
              data-testid="back-to-identity-button"
              type="button"
              onClick={() => { setStage("identity"); setDigits(Array(6).fill("")); }}
              className="w-full text-xs text-muted-foreground hover:text-foreground"
            >
              Gunakan akun lain
            </button>
          </form>
        )}
        <p className="text-[11px] text-muted-foreground mt-8 flex items-start gap-2">
          <ShieldCheck className="w-4 h-4 shrink-0" />
          Akses hanya diberikan setelah identitas akun dan PIN tervalidasi.
        </p>
      </main>
      {document && (
        <DocumentModal
          type={document}
          onClose={() => setDocument(null)}
          onAgree={(type) => {
            setConsent({ ...consent, [type]: true });
            setDocument(null);
          }}
        />
      )}
    </div>
  );
}

function ConsentLinks({ consent, setDocument }) {
  return (
    <p className="text-xs leading-5 text-muted-foreground">
      Dengan melanjutkan, saya menyetujui{" "}
      <button
        data-testid="open-terms-link"
        type="button"
        onClick={() => setDocument("terms")}
        className="text-foreground underline underline-offset-2"
      >
        Syarat & Ketentuan
      </button>{" "}
      {consent.terms && <Check className="inline w-4 h-4 text-emerald-600" />} dan{" "}
      <button
        data-testid="open-privacy-link"
        type="button"
        onClick={() => setDocument("privacy")}
        className="text-foreground underline underline-offset-2"
      >
        Kebijakan Privasi
      </button>{" "}
      {consent.privacy && <Check className="inline w-4 h-4 text-emerald-600" />}.
    </p>
  );
}
