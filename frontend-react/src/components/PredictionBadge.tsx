import { useState, useEffect } from "react";
import { api } from "../api/client";

export default function PredictionBadge({ cazaId, className = "" }: { cazaId: number; className?: string }) {
  const [pred, setPred] = useState<{
    trend: string; prob_baja_7d: number; cambio_pct: number;
    predicted_next: number; max_30d: number; min_30d: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get<{
      predictable: boolean; trend: string; prob_baja_7d: number;
      cambio_pct: number; predicted_next: number; max_30d: number; min_30d: number;
    }>(`/api/predict/${cazaId}`).then(res => {
      if (res.data?.predictable) setPred(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [cazaId]);

  if (loading || !pred) return null;

  const isDown = pred.trend === "bajando";
  const highProb = pred.prob_baja_7d > 65;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium ${highProb ? "bg-green-500/15 text-green-400 border border-green-500/30" : isDown ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20" : "bg-gray-800/40 text-gray-500 border border-gray-700/40"} ${className}`}>
      {highProb ? "📉" : isDown ? "📊" : "📈"} {pred.prob_baja_7d}% bajar
    </span>
  );
}
