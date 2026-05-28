import { useState, useEffect } from "react";
import { api } from "../api/client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const DAY_LABEL: Record<string, string> = {
  Monday: "Lun", Tuesday: "Mar", Wednesday: "Mié", Thursday: "Jue",
  Friday: "Vie", Saturday: "Sáb", Sunday: "Dom",
};

export default function Seasonality({ cazaId }: { cazaId: number | null }) {
  const [data, setData] = useState<Record<string, { avg: number; min: number; max: number; count: number }>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!cazaId) return;
    setLoading(true);
    api.get<{ seasonality: typeof data }>(`/api/kpi/seasonality/${cazaId}`).then(res => {
      if (res.data) setData(res.data.seasonality);
      setLoading(false);
    });
  }, [cazaId]);

  const chartData = DAY_ORDER.filter(d => data[d]).map(d => ({
    day: DAY_LABEL[d] || d,
    avg: data[d].avg,
    min: data[d].min,
    max: data[d].max,
    count: data[d].count,
  }));

  if (!cazaId) return <p className="text-xs text-gray-500 italic">Seleccioná un producto para ver estacionalidad</p>;
  if (loading) return <div className="text-xs text-gray-500 py-2">Analizando...</div>;
  if (!chartData.length) return <p className="text-xs text-gray-500 italic">Sin suficientes datos para estacionalidad</p>;

  return (
    <div>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={chartData}>
          <XAxis dataKey="day" tick={{ fill: "#9ca3af", fontSize: 10 }} />
          <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
          <Tooltip />
          <Bar dataKey="avg" fill="#ef4444" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-2 mt-2">
        {chartData.map(d => (
          <div key={d.day} className="text-[10px] text-gray-500 bg-gray-800/30 rounded px-2 py-1">
            {d.day}: <span className="text-gray-300">${d.avg.toLocaleString()}</span>
            <span className="text-gray-600"> ({d.count} mediciones)</span>
          </div>
        ))}
      </div>
    </div>
  );
}
