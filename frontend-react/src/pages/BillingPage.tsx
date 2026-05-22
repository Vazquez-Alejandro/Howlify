import { useState, useEffect } from "react";
import { api, type StripeSubscription } from "../api/client";
import { useToast } from "../components/Toast";
import PageTransition from "../components/PageTransition";
import SkeletonCard from "../components/SkeletonCard";

const PLAN_LABELS: Record<string, string> = {
  starter: "Starter",
  pro: "Pro",
  business_reseller: "Business Reseller",
  business_monitor: "Business Monitor",
};

const PLAN_LIMITS: Record<string, { cazas: number; precio: string }> = {
  starter: { cazas: 5, precio: "$9/mes" },
  pro: { cazas: 15, precio: "$15/mes" },
  business_reseller: { cazas: 40, precio: "$49/mes" },
  business_monitor: { cazas: 100, precio: "$79/mes" },
};

export default function BillingPage() {
  const { toast } = useToast();
  const [sub, setSub] = useState<StripeSubscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

  useEffect(() => {
    api.getSubscription().then((res) => {
      if (res.data) setSub(res.data);
      setLoading(false);
    });
  }, []);

  const handleUpgrade = async (plan: string) => {
    setCheckoutLoading(plan);
    const res = await api.createCheckout(plan);
    setCheckoutLoading(null);
    if (res.error) {
      toast(res.error, "error");
      return;
    }
    if (res.data?.url) window.location.href = res.data.url;
  };

  const handlePortal = async () => {
    setPortalLoading(true);
    const res = await api.customerPortal();
    setPortalLoading(false);
    if (res.error) {
      toast(res.error, "error");
      return;
    }
    if (res.data?.url) window.location.href = res.data.url;
  };

  if (loading) {
    return <PageTransition><div className="p-6 space-y-4"><SkeletonCard count={3} /></div></PageTransition>;
  }

  const currentPlan = sub?.plan || "starter";

  return (
    <PageTransition>
      <div className="p-4 md:p-8 space-y-8">
        <div>
          <h2 className="text-xl font-bold text-white">💳 Facturación</h2>
          <p className="text-sm text-gray-500">Gestioná tu suscripción y planes</p>
        </div>

        <div className="bg-gray-900/60 rounded-2xl p-5" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Plan actual</h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-2xl font-bold text-white">{PLAN_LABELS[currentPlan] || currentPlan}</p>
              <p className="text-sm text-gray-500 mt-1">{PLAN_LIMITS[currentPlan]?.cazas || "?"} cacerías activas</p>
            </div>
            <button onClick={handlePortal} disabled={portalLoading}
              className="px-4 py-2 bg-gray-800/50 text-gray-300 rounded-xl text-sm hover:bg-gray-700/50 transition-all border border-gray-700/50 disabled:opacity-50 disabled:cursor-not-allowed">
              {portalLoading ? "⏳" : "⚙️ Administrar"}
            </button>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Planes disponibles</h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(PLAN_LIMITS).map(([key, info]) => {
              const isCurrent = key === currentPlan;
              return (
                <div key={key} className={`bg-gray-900/60 rounded-2xl p-5 border transition-all ${isCurrent ? "border-red-500/40 ring-1 ring-red-500/20" : "border-gray-800/50 hover:border-gray-700/50"}`}>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-white text-sm">{info.precio}</h4>
                    {isCurrent && <span className="text-[10px] font-medium text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/20">Actual</span>}
                  </div>
                  <p className="text-lg font-bold text-white mb-3">{PLAN_LABELS[key]}</p>
                  <p className="text-xs text-gray-500 mb-4">{info.cazas} cacerías activas{key === "starter" ? " · 7 días de prueba" : ""}</p>
                  <button onClick={() => handleUpgrade(key)}
                    disabled={isCurrent || checkoutLoading === key}
                    className={`w-full py-2 rounded-xl text-xs font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                      isCurrent
                        ? "bg-gray-800/30 text-gray-600 cursor-not-allowed"
                        : "bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 shadow-lg shadow-red-500/20"
                    }`}>
                    {checkoutLoading === key ? "⏳" : isCurrent ? "Plan actual" : "Seleccionar"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
