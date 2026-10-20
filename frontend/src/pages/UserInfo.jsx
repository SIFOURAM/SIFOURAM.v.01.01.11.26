import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { initials, roleLabel } from "../lib/helpers";
import { useT } from "../lib/i18n";
import { PageHeader, Bento, Field, Empty } from "../components/common";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";

const BANKS = ["Bank BCA", "Bank Mandiri (Livin')", "Bank BRI (BRImo)", "Bank BNI (wondr)", "CIMB Niaga (OCTO Mobile)", "Bank Jago", "SeaBank", "blu by BCA Digital", "Jenius", "Superbank"];

export default function UserInfo() {
  const { t } = useT();
  const [users, setUsers] = useState([]);
  const [edit, setEdit] = useState(null);
  const [creating, setCreating] = useState(false);
  const load = () => api.get("/users").then((r) => setUsers(r.data));
  useEffect(() => { load(); }, []);
  const open = (u) => {
    setCreating(false);
    setEdit({ ...u, banks: u.banks || [], password: "", pin: "" });
  };
  const openCreate = () => {
    setCreating(true);
    setEdit({
      name: "",
      username: "",
      email: "",
      whatsapp: "",
      role: "rider",
      active: true,
      banks: [],
      password: "",
      pin: "",
    });
  };
  const updBank = (i, k, v) => setEdit({ ...edit, banks: edit.banks.map((b, j) => (j === i ? { ...b, [k]: v } : b)) });
  const save = async () => {
    try {
      const payload = {
        name: edit.name,
        username: edit.username,
        email: edit.email,
        whatsapp: edit.whatsapp,
        banks: edit.banks,
        role: edit.role,
        active: edit.active,
      };
      if (edit.password) payload.password = edit.password;
      if (edit.pin) payload.pin = edit.pin;
      if (creating) {
        if (!payload.pin) throw new Error("PIN enam angka wajib diisi untuk akun baru");
        await api.post("/users", payload);
      } else {
        await api.put(`/users/${edit.id}`, payload);
      }
      toast.success(creating ? "Akun dibuat ✓" : "User diperbarui ✓");
      setEdit(null);
      load();
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div data-testid="userinfo-page">
      <PageHeader />
      <Bento testId="userinfo-list">
        <div className="flex items-center justify-between gap-3 mb-4">
          <p className="eyebrow">Semua Pengguna ({users.length})</p>
          <button data-testid="create-user-button" onClick={openCreate} className="btn-primary h-9 px-3 text-xs">
            + Akun
          </button>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          {users.map((u) => (
            <button key={u.id} data-testid={`user-row-${u.id}`} onClick={() => open(u)} className="flex items-center gap-3 p-3 rounded-xl border border-border/60 hover:bg-muted text-left transition-colors">
              <div className="w-10 h-10 rounded-full bg-primary/15 text-primary font-bold flex items-center justify-center overflow-hidden shrink-0">{u.photo ? <img src={u.photo} alt="" className="w-full h-full object-cover" /> : initials(u.name)}</div>
              <div className="flex-1 min-w-0"><p className="font-semibold truncate">{u.name}</p><p className="text-xs text-muted-foreground truncate">@{u.username} · {roleLabel(u.role)} · {u.active === false ? "Nonaktif" : "Aktif"}</p></div>
            </button>))}
        </div>
        {!users.length && <Empty text={t("noData")} />}
      </Bento>

      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent data-testid="user-edit-dialog" className="max-w-lg">
          <DialogHeader><DialogTitle>{creating ? "Buat Akun" : `Edit — ${edit?.name}`}</DialogTitle></DialogHeader>
          {edit && <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
            <Field label="Nama"><input data-testid="ui-name" className="field" value={edit.name || ""} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></Field>
            <Field label="Username"><input data-testid="ui-username" className="field" value={edit.username || ""} onChange={(e) => setEdit({ ...edit, username: e.target.value })} /></Field>
            <Field label="Email"><input data-testid="ui-email" className="field" value={edit.email || ""} onChange={(e) => setEdit({ ...edit, email: e.target.value })} /></Field>
            <Field label="WhatsApp"><input data-testid="ui-wa" className="field" value={edit.whatsapp || ""} onChange={(e) => setEdit({ ...edit, whatsapp: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Role">
                <select data-testid="ui-role" className="field" value={edit.role || "rider"} onChange={(e) => setEdit({ ...edit, role: e.target.value })}>
                  <option value="owner">Owner</option>
                  <option value="admin">Admin</option>
                  <option value="barteam">Bar Team</option>
                  <option value="rider">Rider</option>
                </select>
              </Field>
              <Field label="Status akun">
                <select data-testid="ui-active" className="field" value={String(edit.active !== false)} onChange={(e) => setEdit({ ...edit, active: e.target.value === "true" })}>
                  <option value="true">Aktif</option>
                  <option value="false">Nonaktif</option>
                </select>
              </Field>
            </div>
            <p className="eyebrow pt-1">Rekening Bank</p>
            {edit.banks.map((b, i) => (
              <div key={i} className="rounded-xl border border-border/60 p-3 space-y-2" data-testid={`ui-bank-${i}`}>
                <div className="flex justify-between"><span className="eyebrow">Rekening {i + 1}</span><button type="button" onClick={() => setEdit({ ...edit, banks: edit.banks.filter((_, j) => j !== i) })} className="text-[11px] text-red-500">Hapus</button></div>
                <select className="field" value={b.bank_name || ""} onChange={(e) => updBank(i, "bank_name", e.target.value)}><option value="">— bank —</option>{BANKS.map((x) => <option key={x} value={x}>{x}</option>)}</select>
                <div className="grid grid-cols-2 gap-2"><input className="field num" placeholder="No. Rek" value={b.bank_account || ""} onChange={(e) => updBank(i, "bank_account", e.target.value)} /><input className="field" placeholder="Atas Nama" value={b.bank_holder || ""} onChange={(e) => updBank(i, "bank_holder", e.target.value)} /></div>
              </div>))}
            {edit.banks.length < 3 && <button type="button" onClick={() => setEdit({ ...edit, banks: [...edit.banks, {}] })} className="btn-ghost w-full h-9 text-xs">+ Rekening</button>}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <Field label="Password baru"><input data-testid="ui-password" className="field" placeholder="opsional" value={edit.password} onChange={(e) => setEdit({ ...edit, password: e.target.value })} /></Field>
              <Field label={creating ? "PIN enam angka" : "PIN baru"}><input data-testid="ui-pin" className="field" inputMode="numeric" maxLength={6} placeholder={creating ? "wajib" : "kosong = tetap"} value={edit.pin} onChange={(e) => setEdit({ ...edit, pin: e.target.value.replace(/\D/g, "") })} /></Field>
            </div>
            <button data-testid="ui-save" onClick={save} className="btn-primary w-full">Simpan</button>
          </div>}
        </DialogContent>
      </Dialog>
    </div>
  );
}
