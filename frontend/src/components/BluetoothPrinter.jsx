import { useEffect, useState } from "react";
import { Bluetooth, Link2, Printer, Unplug } from "lucide-react";
import { toast } from "sonner";
import {
  bluetoothPrinterStatus,
  connectBluetoothPrinter,
  disconnectBluetoothPrinter,
  printBluetooth,
} from "../lib/helpers";
import { Bento } from "./common";

export default function BluetoothPrinter() {
  const [status, setStatus] = useState(() => bluetoothPrinterStatus());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const intervalId = setInterval(() => setStatus(bluetoothPrinterStatus()), 2000);
    return () => clearInterval(intervalId);
  }, []);

  const connect = async () => {
    setBusy(true);
    try {
      const nextStatus = await connectBluetoothPrinter();
      setStatus(nextStatus);
      toast.success(`Printer ${nextStatus.name} tersambung`);
    } catch (error) {
      if (error?.name !== "NotFoundError") {
        toast.error(error?.message || "Printer tidak dapat disambungkan");
      }
    } finally {
      setBusy(false);
    }
  };

  const testPrint = async () => {
    setBusy(true);
    try {
      await printBluetooth("SI FOUR AM\nTEST PRINT\nPrinter tersambung\n");
      toast.success("Test print dikirim");
    } catch (error) {
      toast.error(error?.message || "Test print gagal");
    } finally {
      setBusy(false);
    }
  };

  const disconnect = () => {
    disconnectBluetoothPrinter();
    setStatus(bluetoothPrinterStatus());
    toast.success("Printer diputuskan");
  };

  return (
    <Bento className="fade-up" testId="bluetooth-printer-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow mb-1">Thermal Printer</p>
          <p className="text-sm font-semibold">Web Bluetooth · ESC/POS</p>
        </div>
        <Bluetooth className="h-5 w-5 text-primary" />
      </div>
      <p data-testid="bluetooth-printer-status" className="mt-3 text-xs text-muted-foreground">
        {!status.supported
          ? "Gunakan Chrome di Android atau desktop dengan Bluetooth aktif."
          : status.connected
            ? `Tersambung: ${status.name}`
            : "Belum ada printer yang tersambung."}
      </p>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          data-testid="bluetooth-printer-connect"
          onClick={connect}
          disabled={!status.supported || busy}
          className="btn-primary h-11 px-3 text-xs"
        >
          <Link2 className="h-4 w-4" />{status.connected ? "Ganti Printer" : "Sambungkan"}
        </button>
        <button
          data-testid="bluetooth-printer-test"
          onClick={testPrint}
          disabled={!status.connected || busy}
          className="btn-ghost h-11 px-3 text-xs"
        >
          <Printer className="h-4 w-4" />Test Print
        </button>
      </div>
      {status.connected && (
        <button
          data-testid="bluetooth-printer-disconnect"
          onClick={disconnect}
          disabled={busy}
          className="mt-2 flex h-9 items-center gap-2 text-xs text-red-500"
        >
          <Unplug className="h-3.5 w-3.5" />Putuskan printer
        </button>
      )}
    </Bento>
  );
}