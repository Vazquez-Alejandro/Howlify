import { useState, useEffect } from "react";
import { api } from "../api/client";
// recharts imports removed – KPIDashboard only renders cards, no charts

export default function KPIDashboard() {
  const [kpi, setKpi] = useState<Record<string, number> | null>(null);
  const [inflated, setInflated] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const [kpiRes, infRes] = await Promise.all([
        api.get<Record<string, number>>("/api/kpi/summary"),
        api.get<{ inflated: any[] }>("/api/kpi/inflated-prices"),
      ]);
      if (kpiRes.data) setKpi(kpiRes.data);
      if (infRes.data) setInflated(infRes.data.inflated);
      setLoading(false);
    })();
  }, []);

  if (loading || !kpi) return null;

  const cards = [
    { label: "Cacerías activas", value: kpi.total_cazas, icon: "📦", color: "text-white" },
    { label: "Con precio", value: kpi.productos_con_precio, icon: "💰", color: "text-green-400" },
    { label: "Ahorro total", value: `$${kpi.ahorro_total.toLocaleString()}`, icon: "💵", color: "text-emerald-400" },
    { label: "Alertas enviadas", value: kpi.total_alertas, icon: "🔔", color: "text-yellow-400" },
    { label: "Precio promedio", value: `$${kpi.precio_promedio.toLocaleString()}`, icon: "📊", color: "text-blue-400" },
    { label: "Reglas activas", value: kpi.reglas_activas, icon: "⚙️", color: "text-purple-400" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {cards.map(c => (
          <div key={c.label} className="bg-gray-900/60 rounded-xl p-3 border border-gray-800/50">
            <div className="flex items-center justify-between mb-1">
              <span className="text-lg">{c.icon}</span>
              <span className={`text-sm font-bold tabular-nums ${c.color}`}>{c.value}</span>
            </div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">{c.label}</p>
          </div>
        ))}
      </div>

      {inflated.length > 0 && (
        <div className="bg-gray-900/60 rounded-2xl p-4 border border-orange-500/20">
          <h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <span>📉 Posible precio inflado detectado</span>
            <span className="text-[10px] bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded-full">{inflated.length}</span>
          </h4>
          <div className="space-y-2">
            {inflated.map((inf, i) => (
              <div key={i} className="flex items-center justify-between bg-gray-800/30 rounded-lg px-3 py-2 text-xs">
                <div className="min-w-0">
                  <span className="text-gray-200 font-medium">{inf.producto || `#${inf.caza_id}`}</span>
                  <span className="text-gray-500 ml-2">Subió {inf.spike_pct}% → bajó {inf.drop_pct}%</span>
                </div>
                <div className="text-gray-500 shrink-0 ml-2">
                  ${inf.precio_spike.toLocaleString()} → ${inf.precio_drop.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
