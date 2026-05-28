import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import PageTransition from "../components/PageTransition";
import Logo from "../components/Logo";

interface HistoryItem {
  price: number;
  checked_at: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function PublicHistoryPage() {
  const { cazaId } = useParams();
  const [data, setData] = useState<{ producto: string; history: HistoryItem[]; precio_max: number; url: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!cazaId) return;
    fetch(`${API_BASE}/api/public/history/${cazaId}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [cazaId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-red-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-4xl mb-3">🔍</p>
          <p className="text-lg font-medium text-gray-300">Producto no encontrado</p>
          <Link to="/" className="text-sm text-red-400 hover:text-red-300 mt-3 inline-block">Volver al inicio</Link>
        </div>
      </div>
    );
  }

  const chartData = [...data.history].reverse().map(h => ({
    date: new Date(h.checked_at).toLocaleDateString("es-AR", { day: "2-digit", month: "short" }),
    price: h.price,
  }));

  const latest = data.history[0]?.price || 0;
  const avg = data.history.length > 0 ? Math.round(data.history.reduce((a, b) => a + b.price, 0) / data.history.length) : 0;
  const min = data.history.length > 0 ? Math.min(...data.history.map(h => h.price)) : 0;
  const max = data.history.length > 0 ? Math.max(...data.history.map(h => h.price)) : 0;

  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-950">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <div className="text-center mb-8">
            <Logo className="mb-4" size="sm" />
            <h1 className="text-xl font-bold text-white">{data.producto}</h1>
            {data.url && (
              <a href={data.url} target="_blank" rel="noopener noreferrer"
                className="text-sm text-gray-500 hover:text-gray-300 truncate block max-w-md mx-auto mt-1">
                {data.url.slice(0, 60)}
              </a>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              { label: "Último precio", value: `$${latest.toLocaleString()}`, color: "text-white" },
              { label: "Promedio", value: `$${avg.toLocaleString()}`, color: "text-gray-400" },
              { label: "Mínimo histórico", value: `$${min.toLocaleString()}`, color: "text-green-400" },
            ].map(s => (
              <div key={s.label} className="bg-gray-900/60 rounded-xl p-3 text-center" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">{s.label}</p>
                <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>

          <div className="bg-gray-900/60 rounded-2xl p-4 md:p-6" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
            <h2 className="text-sm font-semibold text-gray-300 mb-4">📈 Historial de precios</h2>
            {chartData.length > 1 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} domain={["dataMin - 500", "dataMax + 500"]} />
                  <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px", fontSize: "12px" }}
                    labelStyle={{ color: "#9ca3af" }} formatter={(value: number) => [`$${value.toLocaleString()}`, "Precio"]} />
                  <Line type="monotone" dataKey="price" stroke="#ef4444" strokeWidth={2} dot={{ fill: "#ef4444", r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-sm text-center py-8">Se necesitan al menos 2 mediciones para mostrar el gráfico</p>
            )}
          </div>

          <div className="text-center mt-8">
            <p className="text-xs text-gray-600">
              Monitoreado con <Link to="/" className="text-red-400 hover:text-red-300">Howlify</Link>
              {" · "}
              <button onClick={() => { navigator.share?.({ title: data.producto, url: window.location.href }); }}
                className="text-red-400 hover:text-red-300 text-xs">
                Compartir
              </button>
            </p>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
