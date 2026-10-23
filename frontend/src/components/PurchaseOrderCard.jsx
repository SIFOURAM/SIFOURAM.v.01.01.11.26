import { useState } from "react";
import { Check, Download, Image, MessageCircle, PackageCheck, Send, X } from "lucide-react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { fmtRp, openWA } from "../lib/helpers";
import { Field, PhotoCapture } from "./common";

const STATUS_LABELS = {
  pending: "Menunggu",
  requested: "Menunggu Review Admin",
  reviewed: "Menunggu Persetujuan Owner",
  approved: "Disetujui Owner",
  shipped: "Dalam Pengiriman",
  arrived: "Barang Datang",
  rejected: "Ditolak",
};

const statusClass = (status) => ({
  arrived: "bg-emerald-500/15 text-emerald-600",
  approved: "bg-emerald-500/15 text-emerald-600",
  shipped: "bg-sky-500/15 text-sky-600",
  rejected: "bg-red-500/15 text-red-600",
}[status] || "bg-amber-500/15 text-amber-600");

const poItems = (order) => order.items || [{
  material_id: order.material_id,
  material_name: order.material_name,
  unit: order.unit,
  qty: order.qty,
  unit_price: 0,
  subtotal: 0,
}];

export default function PurchaseOrderCard({ order, user, onChanged }) {
  const [note, setNote] = useState("");
  const [photo, setPhoto] = useState("");
  const [receivedNote, setReceivedNote] = useState("");
  const [busy, setBusy] = useState("");
  const items = poItems(order);
  const status = order.status === "pending" ? "requested" : order.status;

  const act = async (action) => {
    setBusy(action);
    try {
      await api.post(`/purchase-orders/${order.id}/action/${action}`, { note });
      toast.success("Status PO diperbarui.");
      setNote("");
      onChanged();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy("");
    }
  };

  const receive = async () => {
    if (!photo) {
      toast.error("Foto bukti Barang Datang wajib ditambahkan.");
      return;
    }
    setBusy("receive");
    try {
      await api.post(`/purchase-orders/${order.id}/receive`, {
        photo,
        received_note: receivedNote,
      });
      toast.success("Barang diterima dan stok pusat diperbarui.");
      onChanged();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy("");
    }
  };

  const downloadPdf = () => {
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text(`SI FOUR AM — ${order.po_number || "Purchase Order"}`, 14, 16);
    doc.setFontSize(9);
    doc.text(`Vendor: ${order.vendor_name || "-"}`, 14, 23);
    doc.text(`Status: ${STATUS_LABELS[status]}`, 14, 29);
    autoTable(doc, {
      startY: 36,
      head: [["Bahan", "Jumlah", "Harga", "Subtotal"]],
      body: items.map((item) => [
        item.material_name,
        `${item.qty} ${item.unit}`,
        fmtRp(item.unit_price || 0),
        fmtRp(item.subtotal || 0),
      ]),
      headStyles: { fillColor: [255, 107, 0] },
      styles: { fontSize: 8 },
      theme: "grid",
    });
    doc.save(`${order.po_number || "SI-FOUR-AM-PO"}.pdf`);
  };

  const share = async () => {
    const popup = window.open("about:blank", "_blank", "noopener,noreferrer");
    if (!popup) {
      toast.error("Izinkan pop-up untuk membuka WhatsApp.");
      return;
    }
    setBusy("share");
    try {
      await api.post(`/purchase-orders/${order.id}/share-intent`);
      downloadPdf();
      const message = [
        `Halo, berikut ${order.po_number || "Purchase Order"} dari SI FOUR AM.`,
        `Vendor: ${order.vendor_name || "-"}`,
        "Rincian bahan:",
        ...items.map((item) => `• ${item.material_name}: ${item.qty} ${item.unit}`),
        `Estimasi: ${fmtRp(order.total_estimate || 0)}`,
        "PDF PO telah diunduh. Mohon dilampirkan dan dikonfirmasi.",
      ].join("\n");
      popup.location.href = `https://wa.me/6281283578212?text=${encodeURIComponent(message)}`;
      toast.success("PDF diunduh. Lampirkan file tersebut di WhatsApp.");
    } catch (error) {
      popup.close();
      toast.error(errMsg(error));
    } finally {
      setBusy("");
    }
  };

  const canReview = user.role === "admin" && status === "requested";
  const canApprove = user.role === "owner" && status === "reviewed";
  const canReject = (user.role === "admin" && status === "requested") || (
    user.role === "owner" && status === "reviewed"
  );
  const canShip = ["owner", "admin"].includes(user.role) && status === "approved";
  const canReceive = ["owner", "admin", "barteam"].includes(user.role) && status === "shipped";

  return (
    <article className="space-y-4" data-testid={`purchase-order-${order.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-heading font-bold">{order.po_number || "Purchase Order"}</p>
          <p className="text-xs text-muted-foreground">
            {order.requested_by_name} · {order.vendor_name || "Vendor belum diisi"}
          </p>
        </div>
        <span
          data-testid={`purchase-order-status-${order.id}`}
          className={`px-2 py-1 text-xs font-bold uppercase ${statusClass(status)}`}
        >
          {STATUS_LABELS[status]}
        </span>
      </div>

      <div className="space-y-1 border-y border-border/60 py-3 text-xs">
        {items.map((item) => (
          <div key={item.material_id} className="flex items-center justify-between gap-3">
            <span>{item.material_name}</span>
            <span className="num text-muted-foreground">
              {item.qty} {item.unit} · {fmtRp(item.subtotal || 0)}
            </span>
          </div>
        ))}
      </div>

      {order.note && <p className="text-xs text-muted-foreground">{order.note}</p>}
      {order.expected_date && <p className="text-xs">Target tiba: {order.expected_date}</p>}
      {order.decision_note && (
        <p
          data-testid={`purchase-order-decision-${order.id}`}
          className="border-l-2 border-primary pl-2 text-xs"
        >
          {order.decision_note}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          data-testid={`purchase-order-pdf-${order.id}`}
          onClick={downloadPdf}
          className="btn-ghost h-9 px-3 text-xs"
        >
          <Download className="h-3.5 w-3.5" /> PDF
        </button>
        <button
          type="button"
          data-testid={`purchase-order-wa-${order.id}`}
          disabled={busy === "share"}
          onClick={share}
          className="btn-wa h-9 px-3 text-xs"
        >
          <MessageCircle className="h-3.5 w-3.5" /> WhatsApp
        </button>
        {order.arrival_proof && (
          <a
            data-testid={`purchase-order-proof-${order.id}`}
            href={order.arrival_proof}
            target="_blank"
            rel="noreferrer"
            className="btn-ghost h-9 px-3 text-xs"
          >
            <Image className="h-3.5 w-3.5" /> Bukti
          </a>
        )}
      </div>

      {(canReview || canApprove || canReject || canShip) && (
        <div className="space-y-2 border-t border-border/60 pt-3">
          <input
            data-testid={`purchase-order-note-${order.id}`}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className="field h-9 text-xs"
            placeholder="Catatan keputusan (opsional)"
          />
          <div className="flex flex-wrap gap-2">
            {canReview && (
              <button
                type="button"
                data-testid={`purchase-order-review-${order.id}`}
                onClick={() => act("review")}
                disabled={Boolean(busy)}
                className="btn-primary h-9 px-3 text-xs"
              >
                <Check className="h-3.5 w-3.5" /> Review Admin
              </button>
            )}
            {canApprove && (
              <button
                type="button"
                data-testid={`purchase-order-approve-${order.id}`}
                onClick={() => act("approve")}
                disabled={Boolean(busy)}
                className="btn-primary h-9 px-3 text-xs"
              >
                <Check className="h-3.5 w-3.5" /> Setujui Owner
              </button>
            )}
            {canShip && (
              <button
                type="button"
                data-testid={`purchase-order-ship-${order.id}`}
                onClick={() => act("ship")}
                disabled={Boolean(busy)}
                className="btn-primary h-9 px-3 text-xs"
              >
                <Send className="h-3.5 w-3.5" /> Tandai Dikirim
              </button>
            )}
            {canReject && (
              <button
                type="button"
                data-testid={`purchase-order-reject-${order.id}`}
                onClick={() => act("reject")}
                disabled={Boolean(busy)}
                className="btn-ghost h-9 px-3 text-xs"
              >
                <X className="h-3.5 w-3.5" /> Tolak
              </button>
            )}
          </div>
        </div>
      )}

      {canReceive && (
        <div className="space-y-3 border-t border-border/60 pt-3">
          <p className="eyebrow">Barang Datang</p>
          <PhotoCapture
            value={photo}
            onChange={setPhoto}
            label="Foto bukti penerimaan"
            testId={`purchase-order-receive-photo-${order.id}`}
            capture={false}
            fit="contain"
          />
          <Field label="Catatan penerimaan">
            <input
              data-testid={`purchase-order-receive-note-${order.id}`}
              value={receivedNote}
              onChange={(event) => setReceivedNote(event.target.value)}
              className="field"
              placeholder="Jumlah sesuai pesanan"
            />
          </Field>
          <button
            type="button"
            data-testid={`purchase-order-receive-${order.id}`}
            onClick={receive}
            disabled={!photo || busy === "receive"}
            className="btn-primary w-full"
          >
            <PackageCheck className="h-4 w-4" />
            {busy === "receive" ? "Mencatat..." : "Konfirmasi Barang Datang"}
          </button>
        </div>
      )}
    </article>
  );
}