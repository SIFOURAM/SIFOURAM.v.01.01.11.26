import { useEffect, useState } from "react";
import { ExternalLink, MessageCircle } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { waNumber } from "../lib/helpers";
import { Bento, Empty, Field, PageHeader, PhotoCapture } from "../components/common";

const ROLES = ["owner", "admin", "barteam", "rider"];

export function Broadcast() {
  const [roles, setRoles] = useState(["rider"]);
  const [message, setMessage] = useState("");
  const [recipients, setRecipients] = useState([]);
  const send = async () => {
    try {
      const { data } = await api.post("/broadcast", { roles, message });
      setRecipients(data.recipients);
      toast.success(`Notifikasi terkirim ke ${data.recipients.length} pengguna.`);
      const first = data.recipients.find((recipient) => recipient.whatsapp);
      if (first) window.open(`https://wa.me/${waNumber(first.whatsapp)}?text=${encodeURIComponent(message)}`, "_blank", "noopener,noreferrer");
    } catch (error) { toast.error(errMsg(error)); }
  };
  return <div data-testid="broadcast-page"><PageHeader><p className="eyebrow mr-auto">Lainnya · Broadcast</p></PageHeader><Bento gold testId="broadcast-form"><p className="font-heading font-bold text-xl">Broadcast WhatsApp</p><p className="text-xs text-muted-foreground mt-1">Notifikasi aplikasi dikirim ke semua penerima; WhatsApp dibuka dengan pesan yang sama.</p><div className="flex flex-wrap gap-2 mt-5">{ROLES.map((role) => <button key={role} data-testid={`broadcast-role-${role}`} onClick={() => setRoles(roles.includes(role) ? roles.filter((item) => item !== role) : [...roles, role])} className={`px-3 h-9 rounded-lg text-xs font-bold uppercase ${roles.includes(role) ? "bg-primary text-white" : "bg-muted"}`}>{role}</button>)}</div><Field label="Pesan" className="mt-4"><textarea data-testid="broadcast-message-input" className="field min-h-28" value={message} onChange={(event) => setMessage(event.target.value)} /></Field><button data-testid="broadcast-send-button" onClick={send} disabled={!roles.length || !message.trim()} className="btn-primary mt-4"><MessageCircle className="w-4 h-4" />Kirim Broadcast</button></Bento>{recipients.length > 0 && <Bento className="mt-5" testId="broadcast-recipients"><p className="eyebrow mb-3">Penerima</p>{recipients.map((recipient) => <a key={`${recipient.name}-${recipient.whatsapp}`} data-testid={`broadcast-wa-${recipient.name}`} className="flex justify-between py-2 border-b border-border/60 text-sm hover:text-primary" href={`https://wa.me/${waNumber(recipient.whatsapp)}?text=${encodeURIComponent(message)}`} target="_blank" rel="noreferrer"><span>{recipient.name}</span><ExternalLink className="w-4 h-4" /></a>)}</Bento>}</div>;
}

export function PaymentAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [form, setForm] = useState({ name: "", bank_name: "", account_number: "", account_holder: "", active: true, qris_photo: "" });
  const load = () => api.get("/payment-accounts").then((response) => setAccounts(response.data)).catch((error) => toast.error(errMsg(error)));
  useEffect(() => { load(); }, []);
  const save = async (event) => { event.preventDefault(); try { await api.post("/payment-accounts", form); toast.success("Akun pembayaran disimpan."); setForm({ name: "", bank_name: "", account_number: "", account_holder: "", active: true, qris_photo: "" }); load(); } catch (error) { toast.error(errMsg(error)); } };
  return <div data-testid="payment-accounts-page"><PageHeader><p className="eyebrow mr-auto">Lainnya · Owner</p></PageHeader><div className="grid lg:grid-cols-[360px_1fr] gap-6"><Bento gold testId="payment-account-form"><p className="font-heading font-bold text-xl">Akun Pembayaran</p><form onSubmit={save} className="space-y-3 mt-5"><Field label="Nama tampilan"><input data-testid="payment-account-name" className="field" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></Field><Field label="Bank / penyedia"><input data-testid="payment-account-bank" className="field" value={form.bank_name} onChange={(event) => setForm({ ...form, bank_name: event.target.value })} required /></Field><Field label="Nomor rekening"><input data-testid="payment-account-number" className="field num" value={form.account_number} onChange={(event) => setForm({ ...form, account_number: event.target.value })} required /></Field><Field label="Atas nama"><input data-testid="payment-account-holder" className="field" value={form.account_holder} onChange={(event) => setForm({ ...form, account_holder: event.target.value })} required /></Field><p className="eyebrow">QRIS</p><PhotoCapture testId="payment-account-qris-upload" capture={false} value={form.qris_photo} onChange={(qris_photo) => setForm({ ...form, qris_photo })} label="Unggah gambar QRIS" /><button data-testid="payment-account-save" className="btn-primary w-full">Simpan akun</button></form></Bento><div className="grid sm:grid-cols-2 gap-4">{accounts.map((account) => <Bento key={account.id} testId={`payment-account-${account.id}`}><p className="font-heading font-bold">{account.name}</p><p className="text-xs text-muted-foreground">{account.bank_name} · {account.account_number}</p><p className="text-xs mt-1">a.n. {account.account_holder}</p>{account.qris_photo && <img data-testid={`payment-account-qris-${account.id}`} src={account.qris_photo} alt={`QRIS ${account.name}`} className="mt-4 w-full aspect-square object-contain bg-white rounded-lg p-2" />}</Bento>)}{!accounts.length && <Empty text="Belum ada akun pembayaran." />}</div></div></div>;
}