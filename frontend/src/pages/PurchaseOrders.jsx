import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Bento, Empty, PageHeader } from "../components/common";
import PurchaseOrderCard from "../components/PurchaseOrderCard";
import PurchaseOrderForm from "../components/PurchaseOrderForm";

export default function PurchaseOrders() {
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const [materials, setMaterials] = useState([]);
  const [orders, setOrders] = useState([]);
  const load = useCallback(async () => {
    try {
      const [materialResponse, orderResponse] = await Promise.all([
        api.get("/materials"),
        api.get("/purchase-orders"),
      ]);
      setMaterials(materialResponse.data);
      setOrders(orderResponse.data);
    } catch (error) {
      toast.error(errMsg(error));
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  const initialMaterialIds = useMemo(() => {
    const requestedId = searchParams.get("material_id");
    if (requestedId) return [requestedId];
    if (searchParams.get("low_stock") === "1") {
      return materials
        .filter((material) => material.stock <= material.min_stock)
        .map((material) => material.id);
    }
    return [];
  }, [materials, searchParams]);
  return (
    <div data-testid="purchase-orders-page">
      <PageHeader>
        <div className="mr-auto" data-testid="purchase-orders-header">
          <p className="eyebrow">Production</p>
          <h1 className="font-heading text-2xl font-bold">Purchase Order</h1>
        </div>
      </PageHeader>
      <div className="grid lg:grid-cols-[340px_1fr] gap-6">
        <Bento gold testId="purchase-order-form-card">
          <PurchaseOrderForm
            materials={materials}
            initialMaterialIds={initialMaterialIds}
            onCreated={load}
          />
        </Bento>
        <div className="space-y-3">
          <p className="eyebrow">Riwayat Purchase Order</p>
          {orders.map((order) => (
            <Bento key={order.id} testId={`purchase-order-card-${order.id}`}>
              <PurchaseOrderCard order={order} user={user} onChanged={load} />
            </Bento>
          ))}
          {!orders.length && <Empty text="Belum ada Purchase Order." />}
        </div>
      </div>
    </div>
  );
}