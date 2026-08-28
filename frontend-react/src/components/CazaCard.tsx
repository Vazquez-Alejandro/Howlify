import { useState, useEffect, useMemo } from "react";
import { LineChart, Line, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api, type Caza } from "../api/client";
import { useToast } from "./Toast";
import { traducirError } from "../utils/errors";
import Price from "./Price";
import PredictionBadge from "./PredictionBadge";

interface Props {
  caza: Caza;
  onDelete: () => void;
  onUpdate: () => void;
}

export default function CazaCard({ caza, onDelete, onUpdate }: Props) {
  const { toast } = useToast();
  const [results, setResults] = useState<{ title: string; price: number; url: string; price_error?: boolean; price_avg?: number; descuento?: number; match_descuento?: boolean; drop_pct?: number; match_grande?: boolean; precio_personalizado?: boolean; precio_alternativo?: number; stock?: number; inflado_detectado?: boolean; restock_detectado?: boolean; seller?: { seller_id: number; nickname: string; reputation: string; reputation_label: string; total_sales: number; completed_sales: number; positive_ratio: string | null; permalink: string } }[] | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [priceHistory, setPriceHistory] = useState<{ checked_at: string; price: number }[] | null>(null);
  const [showChart, setShowChart] = useState(false);

  const esDescuento = (caza.tipo_alerta || "piso") === "descuento";
  const esGrande = (caza.tipo_alerta || "piso") === "grande";
  const [editForm, setEditForm] = useState({
    keyword: caza.producto || caza.keyword || "",
    url: caza.link || caza.url || "",
    precio_max: caza.precio_max,
    tipo_alerta: caza.tipo_alerta || "piso",
    etiqueta: caza.etiqueta || "",
    precio_venta: caza.precio_venta || 0,
  });

  const kw = (caza.producto || caza.keyword || "Sin nombre").toUpperCase();
  const url = caza.link || caza.url || "";
  const hasPrice = caza.last_price != null;
  const isAlert = esDescuento ? false : hasPrice && caza.last_price! <= caza.precio_max;

  const tendencia = useMemo(() => {
    if (!priceHistory || priceHistory.length < 2) return null;
    const prev = priceHistory[priceHistory.length - 2].price;
    const curr = priceHistory[priceHistory.length - 1].price;
    const diff = curr - prev;
    const pct = prev > 0 ? ((diff / prev) * 100).toFixed(1) : "0";
    return { diff, pct, subio: diff > 0, bajo: diff < 0, estable: diff === 0 };
  }, [priceHistory]);

  useEffect(() => {
    if (!caza.id) return;
    api.getHistory(caza.id).then((res) => {
      if (res.data?.history && res.data.history.length >= 2) {
        setPriceHistory(res.data.history);
      }
    });
  }, [caza.id]);

  const handleHunt = async () => {
    setResults(null);
    setLoadingResults(true);
    const res = await api.hunt(caza.id);
    setLoadingResults(false);
    if (res.data?.results) {
      setResults(res.data.results);
      setShowResults(true);
    }
    onUpdate();
  };

  const handleSave = async () => {
    const res = await api.updateCaza(caza.id, {
      keyword: editForm.keyword,
      url: editForm.url,
      precio_max: editForm.precio_max,
      tipo: editForm.tipo_alerta || "piso",
      etiqueta: editForm.etiqueta,
      precio_venta: editForm.precio_venta || 0,
    });
    if (res.error) {
      toast(traducirError(res.error), "error");
      return;
    }
    setShowEdit(false);
    onUpdate();
    toast("Cacería actualizada", "success");
  };

  return (
    <>
      <div className="bg-gray-900/60 backdrop-blur-sm rounded-2xl border border-gray-800/50 p-4 hover:border-gray-700/50 transition-all duration-200">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-white font-medium truncate">{kw}</p>
              {isAlert && (
                <span className="shrink-0 px-2 py-0.5 text-xs font-medium bg-red-500/10 text-red-400 rounded-lg border border-red-500/20">
                  ALERTA
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-gray-500 text-sm truncate max-w-[180px] sm:max-w-none">{url.slice(0, 55)}</p>
              {caza.etiqueta && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded text-[10px] font-medium border border-purple-500/20 w-fit">
                  🏷️ {caza.etiqueta}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-0.5 flex-wrap">
              {hasPrice && (
                <span className={`text-sm font-medium ${isAlert ? "text-red-400" : "text-green-400"}`}>
                  Últ: <Price amount={caza.last_price!} />
                  {tendencia && (
                    <span className={`ml-1 text-xs ${tendencia.bajo ? "text-green-500" : tendencia.subio ? "text-red-500" : "text-gray-500"}`}>
                      {tendencia.bajo ? "↓" : tendencia.subio ? "↑" : "→"} {tendencia.pct}%
                    </span>
                  )}
                </span>
              )}
              {esDescuento ? (
                <span className="text-sm text-blue-400">
                  Desc: {caza.precio_max || 0}%
                </span>
              ) : (
                <span className="text-sm text-gray-500">
                  Máx: <Price amount={caza.precio_max || 0} />
                </span>
              )}
              {priceHistory && priceHistory.length >= 2 && (
                <button onClick={() => setShowChart(!showChart)}
                  className="px-2 py-0.5 bg-gray-800/30 text-gray-500 rounded-lg text-xs hover:text-gray-300 hover:bg-gray-700/30 transition-all border border-gray-700/30">
                  📊
                </button>
              )}
              <PredictionBadge cazaId={caza.id} />
              <button onClick={() => {
                const url = `${window.location.origin}/p/${caza.id}`;
                if (navigator.share) navigator.share({ title: `Precio de ${kw}`, url });
                else navigator.clipboard.writeText(url).then(() => toast("Link copiado", "success"));
              }}
                className="px-2 py-0.5 bg-gray-800/30 text-gray-500 rounded-lg text-xs hover:text-gray-300 hover:bg-gray-700/30 transition-all border border-gray-700/30">
                🔗
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
            <button
              onClick={handleHunt}
              disabled={loadingResults}
              className="px-3 py-1.5 bg-gray-800/50 text-gray-400 rounded-xl hover:bg-gray-700/50 hover:text-gray-200 text-sm transition-all border border-gray-700/50 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Olfatear"
            >
              {loadingResults ? (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              ) : "🐺"}
            </button>
            <button
              onClick={() => {
                setEditForm({
                  keyword: caza.producto || caza.keyword || "",
                  url: caza.link || caza.url || "",
                  precio_max: caza.precio_max || 0,
                  tipo_alerta: caza.tipo_alerta || "piso",
                  etiqueta: caza.etiqueta || "",
                  precio_venta: caza.precio_venta || 0,
                });
                setShowEdit(true);
              }}
              className="px-3 py-1.5 bg-gray-800/50 text-gray-600 rounded-xl hover:bg-blue-900/30 hover:text-blue-400 text-sm transition-all border border-gray-700/50"
              title="Editar"
            >
              ✏️
            </button>
            {confirmDelete ? (
              <div className="flex items-center gap-1">
                <button
                  onClick={() => { setConfirmDelete(false); onDelete(); }}
                  className="px-2 py-1.5 bg-red-500/20 text-red-400 rounded-xl hover:bg-red-500/30 text-xs font-medium transition-all border border-red-500/30"
                >
                  Sí, eliminar
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-2 py-1.5 bg-gray-800/50 text-gray-500 rounded-xl hover:bg-gray-700/50 hover:text-gray-300 text-xs transition-all border border-gray-700/50"
                >
                  Cancelar
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDelete(true)}
                className="px-3 py-1.5 bg-gray-800/50 text-gray-600 rounded-xl hover:bg-red-900/30 hover:text-red-400 text-sm transition-all border border-gray-700/50"
                title="Eliminar"
              >
                🗑️
              </button>
            )}
          </div>
        </div>

        {loadingResults && (
          <div className="mt-3 pt-3 border-t border-gray-800/50">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <svg className="animate-spin h-4 w-4 text-red-500" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Olfateando...
            </div>
          </div>
        )}

        {results && showResults && results.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-800/50">
            <div className="flex items-center justify-between mb-2">
              <button
                onClick={() => setShowResults(false)}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                Ocultar resultados
              </button>
              <span className="text-xs text-gray-500">{results.length} resultado{results.length !== 1 ? "s" : ""}</span>
            </div>
            <div className="space-y-1">
              {results.slice(0, 5).map((r, i) => (
                <div key={i} className="flex flex-col sm:flex-row sm:items-center justify-between py-1.5 px-2 rounded-lg hover:bg-gray-800/30 transition-colors gap-1">
                  <div className="flex items-center gap-2 min-w-0 flex-1 flex-wrap">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500/50 shrink-0" />
                    <span className="text-gray-300 text-sm truncate max-w-[140px] sm:max-w-none">{r.title?.slice(0, 65)}</span>
                    {r.seller && (
                      <span className="shrink-0 text-[10px] text-gray-500 flex items-center gap-0.5" title={`${r.seller.nickname} — ${r.seller.completed_sales} ventas`}>
                        {r.seller.reputation_label?.split(" ")[0] || "⚪"} {r.seller.nickname?.slice(0, 12)}
                      </span>
                    )}
                    {r.restock_detectado && (
                      <span className="shrink-0 px-1.5 py-0.5 text-[10px] font-bold bg-cyan-500/20 text-cyan-400 rounded border border-cyan-500/30 animate-pulse">
                        🔄 ¡REPUSIERON STOCK!
                      </span>
                    )}
                    {r.inflado_detectado && (
                      <span className="shrink-0 px-1.5 py-0.5 text-[10px] font-bold bg-rose-500/20 text-rose-400 rounded border border-rose-500/30" title="El vendedor infló el precio antes de la 'baja'">
                        🚫 Descuento falso
                      </span>
                    )}
                    {typeof r.stock === "number" && r.stock > 0 && !r.restock_detectado && (
                      <span className="shrink-0 px-1.5 py-0.5 text-[10px] font-bold bg-emerald-500/20 text-emerald-400 rounded border border-emerald-500/30">
                        {r.stock} en stock
                      </span>
                    )}
                    {r.price_error && (
                      <span className="shrink-0 px-1.5 py-0.5 text-[10px] font-bold bg-yellow-500/20 text-yellow-400 rounded border border-yellow-500/30">
                        ERROR PRECIO
                      </span>
                    )}
                    {esDescuento && r.descuento != null && (
                      <span className={`shrink-0 px-1.5 py-0.5 text-[10px] font-bold rounded border ${r.match_descuento ? "bg-green-500/20 text-green-400 border-green-500/30" : "bg-gray-700/30 text-gray-500 border-gray-600/30"}`}>
                        -{r.descuento}%
                      </span>
                    )}
                    {esGrande && r.drop_pct != null && r.drop_pct >= 25 && (
                      <span className="shrink-0 px-1.5 py-0.5 text-[10px] font-bold bg-orange-500/20 text-orange-400 rounded border border-orange-500/30 animate-pulse">
                        🔥 -{r.drop_pct}% OFERTÓN
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`font-medium text-sm ${r.price_error ? "text-yellow-400" : esDescuento && r.match_descuento ? "text-green-400" : esGrande && r.match_grande ? "text-orange-400" : "text-gray-400"}`}><Price amount={r.price || 0} /></span>
                    {r.precio_personalizado && (
                      <span className="shrink-0 px-1.5 py-0.5 text-[10px] font-bold bg-purple-500/20 text-purple-400 rounded border border-purple-500/30" title={`Precio alternativo: $${(r.precio_alternativo || 0).toLocaleString()}`}>
                        🎭 ML variable
                      </span>
                    )}
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2.5 py-1 bg-red-500/10 text-red-400 rounded-lg text-xs hover:bg-red-500/20 transition-all border border-red-500/30 shrink-0 font-medium"
                    >
                      🛒 Comprar
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {results && showResults && results.length === 0 && (
          <div className="mt-3 pt-3 border-t border-gray-800/50">
            <p className="text-sm text-gray-500">Sin resultados en esta ronda</p>
          </div>
        )}

        {showChart && priceHistory && priceHistory.length >= 2 && (
          <div className="mt-3 pt-3 border-t border-gray-800/50">
            <p className="text-xs text-gray-500 mb-2">📈 Historial de precios</p>
            <div className="h-24">
              <MiniChart data={priceHistory} />
            </div>
          </div>
        )}
      </div>

      {showEdit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={() => setShowEdit(false)}>
          <div className="bg-gray-900 rounded-2xl border border-gray-800/50 p-6 w-full max-w-md mx-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-white mb-4">✏️ Editar cacería</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 ml-1 uppercase">Producto / Keyword</label>
                <input value={editForm.keyword} onChange={e => setEditForm(f => ({ ...f, keyword: e.target.value }))}
                  className="w-full mt-0.5 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50" />
              </div>
              <div>
                <label className="text-xs text-gray-400 ml-1 uppercase">URL</label>
                <input value={editForm.url} onChange={e => setEditForm(f => ({ ...f, url: e.target.value }))}
                  className="w-full mt-0.5 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50" />
              </div>
              <div>
                <label className="text-xs text-gray-400 ml-1 uppercase">Tipo de alerta</label>
                <select value={editForm.tipo_alerta} onChange={e => setEditForm(f => ({ ...f, tipo_alerta: e.target.value }))}
                  className="w-full mt-0.5 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50">
                  <option value="piso">Por precio</option>
                  <option value="descuento">Por descuento</option>
                  <option value="grande">Grandes ofertas</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 ml-1 uppercase">{editForm.tipo_alerta === "descuento" ? "Descuento mínimo (%)" : "Precio máximo"}</label>
                <input type="number" value={editForm.precio_max} onChange={e => setEditForm(f => ({ ...f, precio_max: Number(e.target.value) }))}
                  className="w-full mt-0.5 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50" />
              </div>
              <div>
                <label className="text-xs text-gray-400 ml-1 uppercase">Etiqueta</label>
                <input value={editForm.etiqueta} onChange={e => setEditForm(f => ({ ...f, etiqueta: e.target.value }))} placeholder="Ej: Regalo mamá, Para revender"
                  className="w-full mt-0.5 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm placeholder-gray-600 focus:outline-none focus:border-red-500/50" />
              </div>
              {editForm.tipo_alerta === "piso" && (
                <div>
                  <label className="text-xs text-gray-400 ml-1 uppercase">Precio de venta (revendedor)</label>
                  <input type="number" value={editForm.precio_venta || ""} onChange={e => setEditForm(f => ({ ...f, precio_venta: Number(e.target.value) }))} placeholder="Ej: 1500000 — te avisamos tu margen"
                    className="w-full mt-0.5 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm placeholder-gray-600 focus:outline-none focus:border-emerald-500/50" />
                  <p className="text-[11px] text-gray-500 ml-1 mt-1">Howlify te avisa cuando el margen sobre este precio de venta supere el 15%.</p>
                </div>
              )}
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowEdit(false)} className="flex-1 py-2 bg-gray-800 text-gray-400 rounded-lg text-sm font-medium hover:bg-gray-700 transition-all">Cancelar</button>
              <button onClick={handleSave} className="flex-1 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg text-sm font-semibold hover:from-red-600 hover:to-red-700 transition-all shadow-lg shadow-red-500/20">💾 Guardar</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function MiniChart({ data }: { data: { checked_at: string; price: number }[] }) {
  const chartData = data.map((d) => ({
    date: new Date(d.checked_at).toLocaleDateString("es-AR", { day: "2-digit", month: "short" }),
    price: d.price,
  }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={chartData}>
        <YAxis domain={["dataMin - 500", "dataMax + 500"]} hide />
        <Tooltip
          contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px", fontSize: "12px" }}
          labelStyle={{ color: "#9ca3af" }}
          formatter={(value) => [`$${(Number(value) || 0).toLocaleString()}`, "Precio"]}
        />
        <Line type="monotone" dataKey="price" stroke="#ef4444" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
