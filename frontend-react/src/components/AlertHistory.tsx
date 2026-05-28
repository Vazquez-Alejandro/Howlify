import { useState, useEffect } from "react";
import { api } from "../api/client";

export default function AlertHistory() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const res = await api.get<{ alerts: any[] }>("/api/alerts/history");
      if (res.data) setAlerts(res.data.alerts);
      setLoading(false);
    })();
  }, []);

  if (loading) return <div className="text-xs text-gray-500 py-4 text-center">Cargando historial...</div>;
  if (!alerts.length) return <div className="text-xs text-gray-500 py-4 text-center">Sin alertas aún</div>;

  return (
    <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
      {alerts.map((a, i) => {
        const date = a.created_at ? new Date(a.created_at).toLocaleDateString("es-AR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
        return (
          <div key={a.id || i} className="flex items-start gap-2.5 bg-gray-800/30 rounded-lg px-3 py-2 border border-gray-800/50">
            <span className="text-sm shrink-0 mt-0.5">{a.canal === "whatsapp" ? "💬" : a.canal === "push" ? "🔔" : a.canal === "telegram" ? "✈️" : "📧"}</span>
            <div className="min-w-0 flex-1">
              <p className="text-xs text-gray-200 truncate">{a.oferta_titulo || `Producto #${a.caza_id}`}</p>
              <p className="text-[11px] text-gray-500 mt-0.5">
                ${a.oferta_precio?.toLocaleString()} · {a.canal}
              </p>
            </div>
            <span className="text-[10px] text-gray-600 shrink-0">{date}</span>
          </div>
        );
      })}
    </div>
  );
}
