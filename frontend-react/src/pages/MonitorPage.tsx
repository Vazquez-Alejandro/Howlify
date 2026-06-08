import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { api, type Caza, type MonitorRule, type AlertRule, type Grupo } from "../api/client";
import PageTransition from "../components/PageTransition";
import AlertRuleEditor from "../components/AlertRuleEditor";
import KPIDashboard from "../components/KPIDashboard";
import AlertHistory from "../components/AlertHistory";
import Seasonality from "../components/Seasonality";

import {
  ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  BarChart, Bar,
} from "recharts";

type RiskColor = "⚪" | "🔴" | "🟠" | "🟡" | "🟢";

function Sparkline({ data, width = 60, height = 20 }: { data: number[]; width?: number; height?: number }) {
  if (data.length < 2) return <span className="text-gray-600 text-[10px]">—</span>;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * width},${height - ((v - min) / range) * (height - 2) - 1}`).join(" ");
  const color = data[data.length - 1] < data[0] ? "#22c55e" : "#ef4444";
  return (
    <svg width={width} height={height} className="inline-block">
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
    </svg>
  );
}

const RIESGO_LABEL: Record<RiskColor, string> = {
  "⚪": "Sin precio", "🟢": "En rango", "🟡": "Cerca del límite",
  "🟠": "En el límite", "🔴": "Fuera de rango",
};

const COLORS = { verde: "#22c55e", amarillo: "#eab308", naranja: "#f97316", rojo: "#ef4444", gris: "#6b7280" };

export default function MonitorPage() {
  const [cazas, setCazas] = useState<Caza[]>([]);
  const [rules, setRules] = useState<MonitorRule[]>([]);
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [relaciones, setRelaciones] = useState<Record<number, number>>({});
  const [latestPrices, setLatestPrices] = useState<Record<string, { price: number; checked_at: string }>>({});
  const [allHistory, setAllHistory] = useState<{ caza_id: number; price: number; checked_at: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProducto, setSelectedProducto] = useState<string | null>(null);
  const [mode, setMode] = useState<"id" | "grupo">("id");
  const [chartTab, setChartTab] = useState<"general" | "historico" | "ranking" | "estacionalidad">("general");
  const [evidenciaModal, setEvidenciaModal] = useState<string | null>(null);
  const [alertConfig, setAlertConfig] = useState<AlertRule[]>([]);
  const [showAllProducts, setShowAllProducts] = useState(false);
  const [alertHistoryOpen, setAlertHistoryOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [cazasRes, rulesRes, gruposRes, relRes, pricesRes, histRes] = await Promise.all([
        api.listCazas(), api.monitorRules(),
        api.monitorGrupos(), api.monitorGrupoCazas(),
        api.monitorLatestPrices(), api.monitorAllHistory(),
      ]);
      if (cazasRes.data) setCazas(cazasRes.data.cazas);
      if (rulesRes.data) setRules(rulesRes.data.rules);
      if (gruposRes.data) setGrupos(gruposRes.data.grupos);
      if (relRes.data) {
        const map: Record<number, number> = {};
        for (const r of relRes.data.relaciones) map[r.caza_id] = r.grupo_id;
        setRelaciones(map);
      }
      if (pricesRes.data) setLatestPrices(pricesRes.data.prices);
      if (histRes.data) setAllHistory(histRes.data.history);
    } catch {
      // Error silently handled — partial data still renders
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const rulesMap = useMemo(() => new Map(rules.map(r => [r.caza_id, r])), [rules]);

  useEffect(() => {
    if (!selectedProducto) { setAlertConfig([]); return; }
    const row = cazas.find(b => (b.producto || b.keyword || "").toUpperCase() === selectedProducto);
    if (!row) { setAlertConfig([]); return; }
    const rule = rulesMap.get(row.id);
    if (rule?.alert_config && Array.isArray(rule.alert_config)) {
      setAlertConfig(rule.alert_config);
    } else {
      setAlertConfig([]);
    }
  }, [selectedProducto, cazas, rulesMap]);

  const saveAlertConfig = useCallback(async (cazaId: number, config: AlertRule[]) => {
    const existing = rulesMap.get(cazaId);
    const payload: Record<string, unknown> = {
      min_price_allowed: existing?.min_price_allowed || 0,
      max_price_allowed: existing?.max_price_allowed || 0,
      alert_config: config,
    };
    const res = await api.upsertMonitorRule(cazaId, payload);
    if (!res.error) {
      setRules(prev => prev.map(r => r.caza_id === cazaId ? { ...r, alert_config: config } : r));
    }
  }, [rulesMap]);

  const saveAlertTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debouncedSaveAlert = useCallback((cazaId: number, config: AlertRule[]) => {
    if (saveAlertTimer.current) clearTimeout(saveAlertTimer.current);
    saveAlertTimer.current = setTimeout(() => saveAlertConfig(cazaId, config), 800);
  }, [saveAlertConfig]);
  const gruposMap = useMemo(() => new Map(grupos.map(g => [g.id, g])), [grupos]);

  const radarRows = useMemo(() => cazas.map((b) => {
    const bid = b.id;
    const rule = rulesMap.get(bid);
    const lp = latestPrices[String(bid)];
    const currP = lp?.price ?? 0;
    const mP = rule?.min_price_allowed || 0;
    const maxP = rule?.max_price_allowed || 0;
    const hist = allHistory.filter(h => h.caza_id === bid).slice(-20);
    let riesgo: RiskColor = "⚪";
    if (mP > 0 || maxP > 0) {
      if (currP <= 0) riesgo = "⚪";
      else if ((mP > 0 && currP < mP - 0.01) || (maxP > 0 && currP > maxP + 0.01)) riesgo = "🔴";
      else if ((mP > 0 && currP === mP) || (maxP > 0 && currP === maxP)) riesgo = "🟠";
      else if ((mP > 0 && currP <= mP * 1.05) || (maxP > 0 && currP >= maxP * 0.95)) riesgo = "🟡";
      else riesgo = "🟢";
    }
    const gid = relaciones[bid];
    const gInfo = gid ? gruposMap.get(gid) : null;
    return {
      id: bid,
      producto: (b.producto || b.keyword || "SIN NOMBRE").toUpperCase(),
      url: b.link || b.url || "",
      precio: currP,
      minP: mP,
      maxP,
      riesgo,
      grupoId: gid ?? null,
      grupoNombre: gInfo?.nombre || "SIN GRUPO",
      grupoColor: gInfo?.color || "#808080",
      tieneEvidencia: false,
      progreso: mP > 0 && maxP > mP ? Math.max(0, Math.min(1, (currP - mP) / (maxP - mP))) : 0,
      sparkline: hist.map(h => h.price),
    };
  }), [cazas, rulesMap, latestPrices, relaciones, gruposMap, allHistory]);

  const sorted = useMemo(() => {
    const copy = [...radarRows];
    return mode === "grupo"
      ? copy.sort((a, b) => a.grupoNombre.localeCompare(b.grupoNombre) || a.id - b.id)
      : copy.sort((a, b) => a.id - b.id);
  }, [radarRows, mode]);

  const PAGE_SIZE = 10;
  const displayedProducts = showAllProducts ? sorted : sorted.slice(0, PAGE_SIZE);

  const selectedRow = radarRows.find(r => r.producto === selectedProducto);

  const stats = useMemo(() => {
    const total = radarRows.length;
    const conPrecio = radarRows.filter(r => r.precio > 0).length;
    const enRango = radarRows.filter(r => r.riesgo === "🟢").length;
    const violacion = radarRows.filter(r => r.riesgo === "🔴").length;
    const alerta = radarRows.filter(r => r.riesgo === "🟡" || r.riesgo === "🟠").length;
    return { total, conPrecio, enRango, violacion, alerta };
  }, [radarRows]);

  if (loading) {
    return (
      <PageTransition>
        <div className="p-4 md:p-8 space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-gray-900/60 rounded-xl p-4 animate-pulse" style={{ border: "1px solid rgba(107,114,128,0.4)" }}>
                <div className="h-3 bg-gray-800 rounded w-16 mb-3" />
                <div className="h-6 bg-gray-800 rounded w-12" />
              </div>
            ))}
          </div>
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="p-4 md:p-8 space-y-8">
        <div>
          <h2 className="text-xl font-bold text-white">📊 Monitor de Precios</h2>
          <p className="text-sm text-gray-500">Cumplimiento MAP en tiempo real</p>
        </div>

        {cazas.length === 0 ? (
          <div className="text-center py-16 bg-gray-900/40 rounded-2xl" style={{ border: "1px solid rgba(107,114,128,0.4)" }}>
            <p className="text-4xl mb-3">📡</p>
            <p className="text-lg font-medium text-gray-300">Monitor vacío</p>
            <p className="text-sm text-gray-500 mt-1">Primero creá cacerías desde Mis Rastreadores</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Productos", value: stats.total, color: "text-white", icon: "📦" },
                { label: "En cumplimiento", value: stats.enRango, color: "text-green-400", icon: "✅" },
                { label: "Violaciones", value: stats.violacion, color: stats.violacion > 0 ? "text-red-400" : "text-gray-500", icon: "🔴" },
                { label: "Alertas", value: stats.alerta, color: stats.alerta > 0 ? "text-yellow-400" : "text-gray-500", icon: "⚠️" },
              ].map((s) => (
                <div key={s.label} className="bg-gray-900/60 rounded-xl p-4" style={{ border: "1px solid rgba(107,114,128,0.4)" }}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider">{s.label}</span>
                    <span className="text-sm">{s.icon}</span>
                  </div>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                </div>
              ))}
            </div>

            <div className="bg-gray-900/60 rounded-2xl p-4 md:p-6" style={{ border: "1px solid rgba(107,114,128,0.4)" }}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-300">📡 Radar de Precios</h3>
                <div className="flex items-center gap-2">
                  <div className="flex gap-1 bg-gray-800/40 rounded-lg p-0.5">
                    <button onClick={() => setMode("id")} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${mode === "id" ? "bg-red-500/20 text-red-400" : "text-gray-500 hover:text-gray-300"}`}>Individual</button>
                    <button onClick={() => setMode("grupo")} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${mode === "grupo" ? "bg-red-500/20 text-red-400" : "text-gray-500 hover:text-gray-300"}`}>Por grupo</button>
                  </div>
                </div>
              </div>
              <div className="overflow-x-auto overflow-y-auto" style={{ maxHeight: showAllProducts ? "none" : "440px" }}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-500 text-xs uppercase border-b border-gray-800/50 sticky top-0 bg-gray-900/60">
                      <th className="py-3 pr-4">Riesgo</th>
                      <th className="py-3 pr-4">ID</th>
                      <th className="py-3 pr-4 text-left">Producto</th>
                      <th className="py-3 pr-4 text-right">Precio</th>
                      <th className="py-3 pr-4 text-right">MAP Mín</th>
                      <th className="py-3 pr-4 text-right">MAP Máx</th>
                      <th className="py-3 pr-4 text-center">Tendencia</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedProducts.map((row) => (
                      <tr key={row.id} onClick={() => setSelectedProducto(row.producto)} className={`border-b border-gray-800/30 text-gray-300 hover:bg-gray-800/20 cursor-pointer ${selectedProducto === row.producto ? "bg-red-500/5" : ""}`}>
                        <td className="py-3 pr-4 text-lg">{row.riesgo}</td>
                        <td className="py-3 pr-4 text-gray-500 text-xs">{row.id}</td>
                        <td className="py-3 pr-4 font-medium text-white max-w-[200px] truncate">{row.producto}</td>
                        <td className="py-3 pr-4 text-right tabular-nums">{row.precio > 0 ? `$${row.precio.toLocaleString()}` : "-"}</td>
                        <td className="py-3 pr-4 text-right tabular-nums text-red-400">{row.minP > 0 ? `$${row.minP.toLocaleString()}` : "-"}</td>
                        <td className="py-3 pr-4 text-right tabular-nums text-red-400">{row.maxP > 0 ? `$${row.maxP.toLocaleString()}` : "-"}</td>
                        <td className="py-3 pr-4 text-center"><Sparkline data={row.sparkline} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {sorted.length > PAGE_SIZE && (
                <button
                  onClick={() => setShowAllProducts(!showAllProducts)}
                  className="w-full py-2.5 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  {showAllProducts ? "Mostrar menos" : `Mostrar todos (${sorted.length})`}
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-900/60 rounded-2xl p-4 md:p-6" style={{ border: "1px solid rgba(107,114,128,0.4)" }}>
                <h3 className="text-sm font-semibold text-gray-300 mb-4">🔧 Configurar producto</h3>
                <select value={selectedProducto || ""} onChange={(e) => setSelectedProducto(e.target.value || null)} className="w-full mb-4 px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50">
                  <option value="">Seleccionar producto...</option>
                  {radarRows.map((r) => <option key={r.id} value={r.producto}>{r.producto}</option>)}
                </select>
                {selectedRow && (
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: "Precio Actual", value: `$${selectedRow.precio.toLocaleString()}` },
                      { label: "Estado", value: selectedRow.riesgo },
                      { label: "MAP Mín", value: `$${selectedRow.minP.toLocaleString()}` },
                      { label: "MAP Máx", value: `$${selectedRow.maxP.toLocaleString()}` },
                    ].map((s) => (
                      <div key={s.label} className="bg-gray-800/30 rounded-xl p-3 text-center">
                        <p className="text-[10px] text-gray-500 uppercase">{s.label}</p>
                        <p className="text-sm font-bold text-white">{s.value}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="bg-gray-900/60 rounded-2xl p-4 md:p-6" style={{ border: "1px solid rgba(107,114,128,0.4)" }}>
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Configurar alertas</h3>
                {selectedRow ? (
                  <AlertRuleEditor rules={alertConfig} onChange={(newConfig) => { setAlertConfig(newConfig); debouncedSaveAlert(selectedRow.id, newConfig); }} />
                ) : (
                  <p className="text-sm text-gray-500">Seleccioná un producto para configurar alertas</p>
                )}
              </div>
            </div>

            <KPIDashboard />

            <div className="bg-gray-900/60 rounded-2xl p-4 md:p-6" style={{ border: "1px solid rgba(107,114,128,0.4)" }}>
              <div className="flex gap-1 bg-gray-800/40 rounded-lg p-1 mb-5 w-fit overflow-x-auto flex-nowrap">
                {(["general", "historico", "ranking", "estacionalidad"] as const).map((t) => (
                  <button key={t} onClick={() => setChartTab(t)} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all capitalize ${chartTab === t ? "bg-red-500/20 text-red-400" : "text-gray-500 hover:text-gray-300"}`}>
                    {t}
                  </button>
                ))}
              </div>

              {chartTab === "general" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-4">Estado general</h4>
                    <ResponsiveContainer width="100%" height={240}>
                      <PieChart>
                        <Pie
                          data={[
                            { name: "En cumplimiento", value: stats.enRango, color: COLORS.verde },
                            { name: "Alerta", value: stats.alerta, color: COLORS.amarillo },
                            { name: "Violación", value: stats.violacion, color: COLORS.rojo },
                            { name: "Sin datos", value: stats.total - stats.conPrecio, color: COLORS.gris },
                          ].filter((d) => d.value > 0)}
                          cx="50%" cy="50%" innerRadius={55} outerRadius={95} paddingAngle={3} dataKey="value" stroke="none"
                        >
                          {[
                            { name: "En cumplimiento", value: stats.enRango, color: COLORS.verde },
                            { name: "Alerta", value: stats.alerta, color: COLORS.amarillo },
                            { name: "Violación", value: stats.violacion, color: COLORS.rojo },
                            { name: "Sin datos", value: stats.total - stats.conPrecio, color: COLORS.gris },
                          ].filter((d) => d.value > 0).map((entry, i) => (
                            <Cell key={i} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-4">Distribución de precios</h4>
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={radarRows.filter(r => r.precio > 0).map(r => ({
                        name: r.producto.slice(0, 15),
                        precio: r.precio,
                        min: r.minP,
                        max: r.maxP,
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                        <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 9 }} angle={-30} textAnchor="end" height={60} />
                        <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
                        <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px", fontSize: "12px" }} />
                        <Bar dataKey="min" fill={COLORS.rojo} name="MAP Mín" radius={[2, 2, 0, 0]} />
                        <Bar dataKey="precio" fill={COLORS.verde} name="Precio Actual" radius={[2, 2, 0, 0]} />
                        <Bar dataKey="max" fill={COLORS.amarillo} name="MAP Máx" radius={[2, 2, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {chartTab === "historico" && (() => {
                const histData = selectedRow
                  ? allHistory.filter(h => {
                      const caza = cazas.find(c => c.id === h.caza_id);
                      return caza && (caza.producto || caza.keyword) === selectedProducto;
                    })
                  : allHistory;
                const chartData = histData.length > 0 ? (() => {
                  const dateMap = new Map<string, Record<string, number>>();
                  for (const h of histData) {
                    const d = new Date(h.checked_at).toLocaleDateString("es-AR", { day: "2-digit", month: "short" });
                    if (!dateMap.has(d)) dateMap.set(d, {});
                    dateMap.get(d)![String(h.caza_id)] = h.price;
                  }
                  return [...dateMap.entries()].map(([date, prices]) => ({ date, ...prices }));
                })() : [];
                const cazaIds = [...new Set(histData.map(h => h.caza_id))];
                const LINE_COLORS = ["#ef4444", "#22c55e", "#eab308", "#3b82f6", "#a855f7", "#f97316", "#06b6d4"];
                return (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-4">{selectedRow ? `Historial: ${selectedProducto}` : "Historial de precios (todos los productos)"}</h4>
                    {chartData.length > 1 ? (
                      <ResponsiveContainer width="100%" height={280}>
                        <LineChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                          <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                          <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
                          <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px", fontSize: "12px" }} />
                          {cazaIds.slice(0, 7).map((cid, i) => (
                            <Line key={cid} type="monotone" dataKey={String(cid)} stroke={LINE_COLORS[i % LINE_COLORS.length]} strokeWidth={2} dot={false} connectNulls />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="text-gray-500 text-sm text-center py-8">Seleccioná un producto en la tabla o esperá a que se acumulen datos</p>
                    )}
                  </div>
                );
              })()}

              {chartTab === "ranking" && (() => {
                const ranking = [...radarRows]
                  .filter(r => r.precio > 0)
                  .sort((a, b) => {
                    const diffA = a.maxP > 0 && a.minP > 0 ? Math.min(Math.abs(a.precio - a.minP), Math.abs(a.precio - a.maxP)) / (a.maxP - a.minP || 1) : 1;
                    const diffB = b.maxP > 0 && b.minP > 0 ? Math.min(Math.abs(b.precio - b.minP), Math.abs(b.precio - b.maxP)) / (b.maxP - b.minP || 1) : 1;
                    return diffA - diffB;
                  });
                return (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-4">Ranking de cumplimiento MAP</h4>
                    {ranking.length > 0 ? (
                      <ResponsiveContainer width="100%" height={Math.max(240, ranking.length * 36)}>
                        <BarChart data={ranking.map(r => ({
                          name: r.producto.slice(0, 25),
                          violaciones: r.riesgo === "🔴" ? 1 : 0,
                          alertas: r.riesgo === "🟡" || r.riesgo === "🟠" ? 1 : 0,
                          ok: r.riesgo === "🟢" ? 1 : 0,
                        }))} layout="vertical" margin={{ left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                          <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                          <YAxis dataKey="name" type="category" width={130} tick={{ fill: "#9ca3af", fontSize: 10 }} />
                          <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px", fontSize: "12px" }} />
                          <Bar dataKey="ok" stackId="a" fill={COLORS.verde} name="OK" />
                          <Bar dataKey="alertas" stackId="a" fill={COLORS.amarillo} name="Alerta" />
                          <Bar dataKey="violaciones" stackId="a" fill={COLORS.rojo} name="Violación" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="text-gray-500 text-sm text-center py-8">No hay datos suficientes para el ranking</p>
                    )}
                  </div>
                );
              })()}

              {chartTab === "estacionalidad" && <Seasonality cazaId={selectedRow?.id ?? null} />}
            </div>

            <div className="bg-gray-900/60 rounded-2xl overflow-hidden" style={{ border: "1px solid rgba(107,114,128,0.4)" }}>
              <button onClick={() => setAlertHistoryOpen(!alertHistoryOpen)} className="w-full flex items-center justify-between px-4 md:px-6 py-4 text-left hover:bg-gray-800/20 transition-colors">
                <h3 className="text-sm font-semibold text-gray-300">Historial de alertas</h3>
                <span className="text-gray-500 text-xs">{alertHistoryOpen ? "▾" : "▸"}</span>
              </button>
              {alertHistoryOpen && (
                <div className="px-4 md:px-6 pb-4 md:pb-6">
                  <AlertHistory />
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 bg-gray-900/40 rounded-xl px-5 py-3" style={{ border: "1px solid rgba(107,114,128,0.4)" }}>
              <span className="text-gray-400 font-medium">Leyenda:</span>
              {(["🟢", "🟡", "🟠", "🔴", "⚪"] as RiskColor[]).map((r) => (
                <span key={r} className="flex items-center gap-1">{r} {RIESGO_LABEL[r]}</span>
              ))}
            </div>
          </>
        )}

        {evidenciaModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={() => setEvidenciaModal(null)}>
            <div className="relative max-w-3xl max-h-[90vh] mx-4" onClick={(e) => e.stopPropagation()}>
              <button onClick={() => setEvidenciaModal(null)} className="absolute top-2 right-2 w-8 h-8 bg-gray-900 rounded-full border border-gray-700 text-gray-400 hover:text-white flex items-center justify-center z-10">✕</button>
              <img src={`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/monitor/evidencia/${evidenciaModal}?token=${localStorage.getItem("token") || ""}`} alt="Evidencia" className="max-w-full max-h-[90vh] rounded-2xl border border-gray-700/50 shadow-2xl" />
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  );
}
