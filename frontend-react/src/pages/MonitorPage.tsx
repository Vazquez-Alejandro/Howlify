import { useState, useEffect } from "react";
import { api, type Caza, type MonitorRule, type Infraccion, type Grupo } from "../api/client";
import { useToast } from "../components/Toast";
import PageTransition from "../components/PageTransition";
import SkeletonCard from "../components/SkeletonCard";

type RiskColor = "⚪" | "🔴" | "🟠" | "🟡" | "🟢";

interface RadarRow {
  id: number;
  producto: string;
  url: string;
  precio: number;
  minP: number;
  maxP: number;
  riesgo: RiskColor;
  grupoId: number | null;
  grupoNombre: string;
  grupoColor: string;
  tieneEvidencia: boolean;
  progreso: number;
}

const EMOJIS = ["📁", "🏷️", "🔥", "📦", "🛒", "💎", "🚀", "📊", "🔍", "✅", "⚠️", "✈️", "🌍", "🇦🇷", "🎸", "🎮"];

const RIESGO_LABEL: Record<RiskColor, { label: string; color: string }> = {
  "⚪": { label: "Sin precio", color: "text-gray-500" },
  "🟢": { label: "En rango", color: "text-green-400" },
  "🟡": { label: "Cerca del límite", color: "text-yellow-400" },
  "🟠": { label: "En el límite", color: "text-orange-400" },
  "🔴": { label: "Fuera de rango", color: "text-red-400" },
};

export default function MonitorPage() {
  const { toast } = useToast();
  const [cazas, setCazas] = useState<Caza[]>([]);
  const [rules, setRules] = useState<MonitorRule[]>([]);
  const [infracciones, setInfracciones] = useState<Infraccion[]>([]);
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [relaciones, setRelaciones] = useState<Record<number, number>>({});
  const [priceHistory, setPriceHistory] = useState<Record<number, { checked_at: string; price: number }[]>>({});
  const [loading, setLoading] = useState(true);
  const [selectedProducto, setSelectedProducto] = useState<string | null>(null);
  const [mode, setMode] = useState<"id" | "grupo">("id");
  const [evidenciaModal, setEvidenciaModal] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    const [cazasRes, rulesRes, infRes, gruposRes, relRes] = await Promise.all([
      api.listCazas(),
      api.monitorRules(),
      api.monitorInfracciones(),
      api.monitorGrupos(),
      api.monitorGrupoCazas(),
    ]);
    if (cazasRes.data) setCazas(cazasRes.data.cazas);
    if (rulesRes.data) setRules(rulesRes.data.rules);
    if (infRes.data) setInfracciones(infRes.data.infracciones);
    if (gruposRes.data) setGrupos(gruposRes.data.grupos);
    if (relRes.data) {
      const map: Record<number, number> = {};
      for (const r of relRes.data.relaciones) map[r.caza_id] = r.grupo_id;
      setRelaciones(map);
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const rulesMap = new Map(rules.map(r => [r.caza_id, r]));
  const gruposMap = new Map(grupos.map(g => [g.id, g]));
  const infraMap = new Map<string, Infraccion>();
  for (const i of infracciones) {
    const key = String(i.caza_id);
    if (!infraMap.has(key)) infraMap.set(key, i);
  }

  const radarRows: RadarRow[] = cazas
    .map((b) => {
      const bid = b.id;
      const rule = rulesMap.get(bid);
      const inf = infraMap.get(String(bid));
      const currP = 0;
      const mP = rule?.min_price_allowed || 0;
      const maxP = rule?.max_price_allowed || 0;
      const tolerancia = 0.05;
      let riesgo: RiskColor = "⚪";
      if (mP > 0 || maxP > 0) {
        if ((mP > 0 && currP > 0 && currP < mP - 0.01) || (maxP > 0 && currP > 0 && currP > maxP + 0.01)) riesgo = "🔴";
        else if ((mP > 0 && currP > 0 && currP === mP) || (maxP > 0 && currP > 0 && currP === maxP)) riesgo = "🟠";
        else if ((mP > 0 && currP > 0 && currP <= mP * (1 + tolerancia)) || (maxP > 0 && currP > 0 && currP >= maxP * (1 - tolerancia))) riesgo = "🟡";
        else if (mP > 0 || maxP > 0) riesgo = "🟢";
      }
      const progreso = mP > 0 && maxP > mP ? Math.max(0, Math.min(1, (currP - mP) / (maxP - mP))) : 0;
      const gid = relaciones[bid];
      const gInfo = gid ? gruposMap.get(gid) : null;
      return {
        id: bid,
        producto: (b.producto || b.keyword || "SIN NOMBRE").toUpperCase(),
        url: b.link || b.url || "",
        precio: currP,
        minP: mP,
        maxP: maxP,
        riesgo,
        grupoId: gid ?? null,
        grupoNombre: gInfo?.nombre || "SIN GRUPO",
        grupoColor: gInfo?.color || "#808080",
        tieneEvidencia: !!(inf?.url_captura && inf.url_captura.trim()),
        progreso,
      } satisfies RadarRow;
    });

  const sorted = mode === "grupo"
    ? [...radarRows].sort((a, b) => a.grupoNombre.localeCompare(b.grupoNombre) || a.id - b.id)
    : [...radarRows].sort((a, b) => a.id - b.id);

  const selectedRow = radarRows.find(r => r.producto === selectedProducto);

  const [mapForm, setMapForm] = useState({ min: 0, max: 0, grupoId: 0 });

  useEffect(() => {
    if (selectedRow) setMapForm({ min: selectedRow.minP, max: selectedRow.maxP, grupoId: selectedRow.grupoId ?? 0 });
  }, [selectedProducto]);

  const [newGrupoName, setNewGrupoName] = useState("");
  const [newGrupoEmoji, setNewGrupoEmoji] = useState("📁");

  const handleSaveConfig = async () => {
    if (!selectedRow) return;
    await api.upsertMonitorRule(selectedRow.id, {
      product_name: selectedRow.producto,
      product_url: selectedRow.url,
      source: "generic",
      min_price_allowed: mapForm.min,
      max_price_allowed: mapForm.max,
    });
    await api.assignMonitorGrupo(selectedRow.id, mapForm.grupoId || null);
    await loadData();
    toast("Configuración guardada", "success");
  };

  const handleCreateGrupo = async () => {
    if (!newGrupoName.trim()) return;
    await api.createMonitorGrupo(newGrupoName.trim(), newGrupoEmoji);
    await loadData();
    setNewGrupoName("");
    toast("Grupo creado", "success");
  };

  const handleDeleteGrupo = async (id: number) => {
    await api.deleteMonitorGrupo(id);
    await loadData();
    toast("Grupo eliminado", "success");
  };

  const loadPriceHistory = async (cazaId: number) => {
    if (priceHistory[cazaId]) return;
    const res = await api.monitorPriceHistory(cazaId);
    if (res.data) setPriceHistory(prev => ({ ...prev, [cazaId]: res.data!.history }));
  };

  if (loading) return <PageTransition><div className="p-6 max-w-5xl mx-auto"><SkeletonCard count={4} /></div></PageTransition>;

  return (
    <PageTransition>
      <div className="p-4 md:p-6 max-w-6xl mx-auto space-y-6">
        <div>
          <h2 className="text-xl font-bold text-white">📊 Control de Precios · Monitor</h2>
          <p className="text-sm text-gray-500">Supervisá el cumplimiento de precios y salud de canal en tiempo real.</p>
        </div>

        {cazas.length === 0 ? (
          <div className="text-center py-12 bg-gray-900/40 rounded-2xl border border-gray-800/50">
            <p className="text-gray-400">No hay productos monitoreados.</p>
          </div>
        ) : (
          <>
            {/* Radar table */}
            <div className="bg-gray-900/60 rounded-2xl border border-gray-800/50 p-4 md:p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-gray-300">📡 Radar de Precios Global</h3>
                <div className="flex gap-1 bg-gray-800/40 rounded-lg p-0.5">
                  <button onClick={() => setMode("id")} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${mode === "id" ? "bg-red-500/20 text-red-400" : "text-gray-500 hover:text-gray-300"}`}>Orden por ID</button>
                  <button onClick={() => setMode("grupo")} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${mode === "grupo" ? "bg-red-500/20 text-red-400" : "text-gray-500 hover:text-gray-300"}`}>Agrupar</button>
                </div>
              </div>

              {/* Desktop table */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-500 text-xs uppercase border-b border-gray-800/50">
                      {mode === "grupo" && <th className="py-2 pr-2"></th>}
                      {mode === "grupo" && <th className="py-2 pr-3">Grupo</th>}
                      <th className="py-2 pr-3">Riesgo</th>
                      <th className="py-2 pr-3">ID</th>
                      <th className="py-2 pr-3 text-left">Producto</th>
                      <th className="py-2 pr-3 text-right">Precio</th>
                      <th className="py-2 pr-3 text-right">Mín. MAP</th>
                      <th className="py-2 pr-3 text-right">Máximo</th>
                      <th className="py-2 pr-3">Evidencia</th>
                      <th className="py-2">Rango</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((row) => (
                      <tr key={row.id} className="border-b border-gray-800/30 text-gray-300 hover:bg-gray-800/20 cursor-pointer" onClick={() => { setSelectedProducto(row.producto); loadPriceHistory(row.id); }}>
                        {mode === "grupo" && (
                          <td className="py-2 pr-2">{row.grupoColor.startsWith("#") ? "📁" : row.grupoColor}</td>
                        )}
                        {mode === "grupo" && <td className="py-2 pr-3 text-xs text-gray-500">{row.grupoNombre}</td>}
                        <td className="py-2 pr-3 text-lg">{row.riesgo}</td>
                        <td className="py-2 pr-3 text-gray-500">{row.id}</td>
                        <td className="py-2 pr-3 font-medium text-white max-w-[200px] truncate">{row.producto}</td>
                        <td className="py-2 pr-3 text-right">{row.precio > 0 ? `$${row.precio.toLocaleString()}` : "-"}</td>
                        <td className="py-2 pr-3 text-right text-red-400">{row.minP > 0 ? `$${row.minP.toLocaleString()}` : "-"}</td>
                        <td className="py-2 pr-3 text-right text-red-400">{row.maxP > 0 ? `$${row.maxP.toLocaleString()}` : "-"}</td>
                        <td className="py-2 pr-3 text-center">{row.tieneEvidencia ? <button onClick={(e) => { e.stopPropagation(); setEvidenciaModal(String(row.id)); }} className="text-sm cursor-pointer hover:scale-110 transition-transform" title="Ver evidencia">📸</button> : null}</td>
                        <td className="py-2">
                          <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${row.riesgo === "🔴" ? "bg-red-500" : row.riesgo === "🟠" ? "bg-orange-500" : row.riesgo === "🟡" ? "bg-yellow-500" : "bg-green-500"}`} style={{ width: `${row.progreso * 100}%` }} />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <div className="md:hidden space-y-2">
                {sorted.map((row) => (
                  <div key={row.id} onClick={() => { setSelectedProducto(row.producto); loadPriceHistory(row.id); }} className="bg-gray-800/30 rounded-xl p-3 border border-gray-800/50 cursor-pointer">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-500">#{row.id}</span>
                      <span className="text-lg">{row.riesgo}</span>
                    </div>
                    <p className="text-sm font-medium text-white truncate">{row.producto}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                      <span>MAP: ${row.minP.toLocaleString()} - ${row.maxP.toLocaleString()}</span>
                      {row.tieneEvidencia && <button onClick={(e) => { e.stopPropagation(); setEvidenciaModal(String(row.id)); }} className="text-red-400 hover:scale-110 transition-transform" title="Ver evidencia">📸</button>}
                      {mode === "grupo" && <span>{row.grupoNombre}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Configuration form */}
            <div className="bg-gray-900/60 rounded-2xl border border-gray-800/50 p-4 md:p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">🔧 Configurar producto</h3>
              <select
                value={selectedProducto || ""}
                onChange={(e) => { setSelectedProducto(e.target.value || null); if (e.target.value) loadPriceHistory(radarRows.find(r => r.producto === e.target.value)!.id); }}
                className="w-full mb-4 px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50"
              >
                <option value="">Seleccionar producto...</option>
                {radarRows.map(r => <option key={r.id} value={r.producto}>{r.producto}</option>)}
              </select>
              {selectedRow && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                      <p className="text-xs text-gray-500">Precio Actual</p>
                      <p className="text-lg font-bold text-white">{selectedRow.precio > 0 ? `$${selectedRow.precio.toLocaleString()}` : "-"}</p>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                      <p className="text-xs text-gray-500">Estado</p>
                      <p className="text-lg">{selectedRow.riesgo}</p>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                      <p className="text-xs text-gray-500">MAP Configurado</p>
                      <p className="text-lg font-bold text-white">${selectedRow.minP.toLocaleString()}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <label className="text-xs text-gray-400 ml-1">MAP (Mínimo)</label>
                      <input type="number" value={mapForm.min} onChange={e => setMapForm(f => ({ ...f, min: Number(e.target.value) }))}
                        className="w-full mt-1 px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 ml-1">Techo (Máximo)</label>
                      <input type="number" value={mapForm.max} onChange={e => setMapForm(f => ({ ...f, max: Number(e.target.value) }))}
                        className="w-full mt-1 px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 ml-1">Asignar a Grupo</label>
                      <select value={mapForm.grupoId} onChange={e => setMapForm(f => ({ ...f, grupoId: Number(e.target.value) }))}
                        className="w-full mt-1 px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50">
                        <option value={0}>Sin Grupo</option>
                        {grupos.map(g => <option key={g.id} value={g.id}>{g.color} {g.nombre}</option>)}
                      </select>
                    </div>
                  </div>

                  <button onClick={handleSaveConfig}
                    className="w-full py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold hover:from-red-600 hover:to-red-700 transition-all shadow-lg shadow-red-500/20">
                    💾 Guardar Cambios
                  </button>

                  {/* Price history */}
                  {priceHistory[selectedRow.id] && priceHistory[selectedRow.id].length > 1 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-300 mb-2">📈 Historial de Precios</h4>
                      <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-800/50">
                        <div className="flex items-end gap-1 h-24">
                          {priceHistory[selectedRow.id].map((h, i) => {
                            const maxPrice = Math.max(...priceHistory[selectedRow.id].map(x => x.price));
                            const pct = maxPrice > 0 ? (h.price / maxPrice) * 100 : 0;
                            const isViolation = selectedRow.minP > 0 && h.price < selectedRow.minP;
                            return (
                              <div key={i} className="flex-1 flex flex-col items-center group relative">
                                <div className={`w-full rounded-t ${isViolation ? "bg-red-500" : "bg-red-500/40"}`}
                                  style={{ height: `${pct}%`, minHeight: "4px" }} />
                                <div className="absolute bottom-full mb-1 hidden group-hover:block bg-gray-900 text-xs text-white px-2 py-1 rounded whitespace-nowrap">
                                  ${h.price.toLocaleString()} - {new Date(h.checked_at).toLocaleDateString()}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        {selectedRow.minP > 0 && <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                          <div className="w-3 h-3 rounded bg-red-500" /> MAP mínimo: ${selectedRow.minP.toLocaleString()}
                        </div>}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Group management */}
            <div className="bg-gray-900/60 rounded-2xl border border-gray-800/50 p-4 md:p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">⚙️ Gestión de Grupos</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-800/50">
                  <p className="text-sm font-medium text-gray-300 mb-3">Nuevo Grupo</p>
                  <input value={newGrupoName} onChange={e => setNewGrupoName(e.target.value)} placeholder="Ej: Importaciones"
                    className="w-full mb-2 px-4 py-2 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50" />
                  <div className="flex gap-1 flex-wrap mb-3">
                    {EMOJIS.map(e => (
                      <button key={e} onClick={() => setNewGrupoEmoji(e)}
                        className={`w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-all ${newGrupoEmoji === e ? "bg-red-500/20 border border-red-500/30" : "bg-gray-700/30 border border-transparent hover:bg-gray-700/50"}`}>{e}</button>
                    ))}
                  </div>
                  <button onClick={handleCreateGrupo} className="w-full py-2 bg-red-500/10 text-red-400 rounded-xl text-sm font-medium hover:bg-red-500/20 transition-all border border-red-500/20">Guardar</button>
                </div>
                <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-800/50">
                  <p className="text-sm font-medium text-gray-300 mb-3">Eliminar Existente</p>
                  {grupos.length === 0 ? (
                    <p className="text-sm text-gray-500">No hay grupos creados.</p>
                  ) : (
                    <select
                      value=""
                      onChange={e => { if (e.target.value) handleDeleteGrupo(Number(e.target.value)); }}
                      className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50"
                    >
                      <option value="">Seleccionar grupo...</option>
                      {grupos.map(g => <option key={g.id} value={g.id}>{g.color} {g.nombre}</option>)}
                    </select>
                  )}
                </div>
              </div>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 bg-gray-900/40 rounded-xl px-4 py-3 border border-gray-800/50">
              <span>Leyenda:</span>
              {(["🟢", "🟡", "🟠", "🔴", "⚪"] as RiskColor[]).map(r => (
                <span key={r}>{r} {RIESGO_LABEL[r].label}</span>
              ))}
            </div>
          </>
        )}

        {/* Evidence modal */}
        {evidenciaModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={() => setEvidenciaModal(null)}>
            <div className="relative max-w-3xl max-h-[90vh] mx-4" onClick={(e) => e.stopPropagation()}>
              <button onClick={() => setEvidenciaModal(null)} className="absolute -top-3 -right-3 w-8 h-8 bg-gray-900 rounded-full border border-gray-700 text-gray-400 hover:text-white flex items-center justify-center z-10">
                ✕
              </button>
              <img src={`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/monitor/evidencia/${evidenciaModal}`} alt="Evidencia"
                className="max-w-full max-h-[90vh] rounded-2xl border border-gray-700/50 shadow-2xl" />
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  );
}
