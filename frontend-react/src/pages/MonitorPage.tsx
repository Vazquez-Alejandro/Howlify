import { useState, useEffect, useMemo } from "react";
import { api, type Caza, type MonitorRule, type Infraccion, type Grupo } from "../api/client";
import { useToast } from "../components/Toast";
import PageTransition from "../components/PageTransition";
import SkeletonCard from "../components/SkeletonCard";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, ScatterChart, Scatter, CartesianGrid,
} from "recharts";

type RiskColor = "⚪" | "🔴" | "🟠" | "🟡" | "🟢";
type ChartTab = "general" | "historico" | "alertas" | "ranking";

function InfoButton({ description }: { description: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative inline-block">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        className="w-4 h-4 rounded-full bg-gray-800/50 text-gray-500 hover:text-red-400 hover:bg-gray-700/50 border border-gray-700/50 flex items-center justify-center transition-all text-[10px] font-bold leading-none"
        title="¿Qué es esto?"
      >
        i
      </button>
      {open && (
        <div className="absolute top-5 left-1/2 -translate-x-1/2 z-40 w-64 bg-gray-900 border border-gray-700/50 rounded-xl p-3 shadow-2xl text-xs text-gray-300 leading-relaxed backdrop-blur-xl"
          onClick={(e) => e.stopPropagation()}>
          <p>{description}</p>
          <button onClick={() => setOpen(false)} className="mt-2 text-red-400 hover:text-red-300 text-[10px] font-medium">Cerrar</button>
        </div>
      )}
    </div>
  );
}

const RIESGO_LABEL: Record<RiskColor, string> = {
  "⚪": "Sin precio", "🟢": "En rango", "🟡": "Cerca del límite",
  "🟠": "En el límite", "🔴": "Fuera de rango",
};

const EMOJIS = ["📁", "🏷️", "🔥", "📦", "🛒", "💎", "🚀", "📊", "🔍", "✅", "⚠️", "✈️", "🌍", "🇦🇷", "🎸", "🎮"];

const COLORS = { verde: "#22c55e", amarillo: "#eab308", naranja: "#f97316", rojo: "#ef4444", gris: "#6b7280" };

export default function MonitorPage() {
  const { toast } = useToast();
  const [cazas, setCazas] = useState<Caza[]>([]);
  const [rules, setRules] = useState<MonitorRule[]>([]);
  const [infracciones, setInfracciones] = useState<Infraccion[]>([]);
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [relaciones, setRelaciones] = useState<Record<number, number>>({});
  const [latestPrices, setLatestPrices] = useState<Record<string, { price: number; checked_at: string }>>({});
  const [allHistory, setAllHistory] = useState<{ caza_id: number; price: number; checked_at: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProducto, setSelectedProducto] = useState<string | null>(null);
  const [mode, setMode] = useState<"id" | "grupo">("id");
  const [chartTab, setChartTab] = useState<ChartTab>("general");
  const [evidenciaModal, setEvidenciaModal] = useState<string | null>(null);
  const [assigningGroup, setAssigningGroup] = useState<number | null>(null);

  const loadData = async () => {
    setLoading(true);
    const [cazasRes, rulesRes, infRes, gruposRes, relRes, pricesRes, histRes] = await Promise.all([
      api.listCazas(), api.monitorRules(), api.monitorInfracciones(),
      api.monitorGrupos(), api.monitorGrupoCazas(),
      api.monitorLatestPrices(), api.monitorAllHistory(),
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
    if (pricesRes.data) setLatestPrices(pricesRes.data.prices);
    if (histRes.data) setAllHistory(histRes.data.history);
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  useEffect(() => {
    if (assigningGroup !== null) {
      const close = () => setAssigningGroup(null);
      document.addEventListener("click", close);
      return () => document.removeEventListener("click", close);
    }
  }, [assigningGroup]);

  // Derived data
  const rulesMap = useMemo(() => new Map(rules.map(r => [r.caza_id, r])), [rules]);
  const gruposMap = useMemo(() => new Map(grupos.map(g => [g.id, g])), [grupos]);
  const infraMap = useMemo(() => {
    const m = new Map<string, Infraccion>();
    for (const i of infracciones) { const k = String(i.caza_id); if (!m.has(k)) m.set(k, i); }
    return m;
  }, [infracciones]);

  const radarRows = useMemo(() => cazas.map((b) => {
    const bid = b.id;
    const rule = rulesMap.get(bid);
    const inf = infraMap.get(String(bid));
    const lp = latestPrices[String(bid)];
    const currP = lp?.price || 0;
    const mP = rule?.min_price_allowed || 0;
    const maxP = rule?.max_price_allowed || 0;
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
      maxP: maxP,
      riesgo,
      grupoId: gid ?? null,
      grupoNombre: gInfo?.nombre || "SIN GRUPO",
      grupoColor: gInfo?.color || "#808080",
      tieneEvidencia: !!(inf?.url_captura && inf.url_captura.trim()),
      progreso: mP > 0 && maxP > mP ? Math.max(0, Math.min(1, (currP - mP) / (maxP - mP))) : 0,
    };
  }), [cazas, rulesMap, infraMap, latestPrices, relaciones, gruposMap]);

  const sorted = useMemo(() => {
    const copy = [...radarRows];
    return mode === "grupo"
      ? copy.sort((a, b) => a.grupoNombre.localeCompare(b.grupoNombre) || a.id - b.id)
      : copy.sort((a, b) => a.id - b.id);
  }, [radarRows, mode]);

  const selectedRow = radarRows.find(r => r.producto === selectedProducto);

  // Stats
  const stats = useMemo(() => {
    const total = radarRows.length;
    const conPrecio = radarRows.filter(r => r.precio > 0).length;
    const enRango = radarRows.filter(r => r.riesgo === "🟢").length;
    const violacion = radarRows.filter(r => r.riesgo === "🔴").length;
    const alerta = radarRows.filter(r => r.riesgo === "🟡" || r.riesgo === "🟠").length;
    return { total, conPrecio, enRango, violacion, alerta };
  }, [radarRows]);

  // Chart data
  const complianceData = useMemo(() => [
    { name: "En cumplimiento", value: stats.enRango, color: COLORS.verde },
    { name: "Alerta", value: stats.alerta, color: COLORS.amarillo },
    { name: "Violación", value: stats.violacion, color: COLORS.rojo },
    { name: "Sin datos", value: stats.total - stats.conPrecio, color: COLORS.gris },
  ], [stats]);

  const historyByCaza = useMemo(() => {
    const map: Record<number, { checked_at: string; price: number }[]> = {};
    for (const h of allHistory) {
      if (!map[h.caza_id]) map[h.caza_id] = [];
      map[h.caza_id].push(h);
    }
    return map;
  }, [allHistory]);

  const selectedHistory = selectedRow ? historyByCaza[selectedRow.id] || [] : [];

  // Infracción count per caza
  const infraCount = useMemo(() => {
    const map: Record<number, number> = {};
    for (const i of infracciones) {
      const k = i.caza_id;
      map[k] = (map[k] || 0) + 1;
    }
    return map;
  }, [infracciones]);

  const rankingData = useMemo(() => {
    return radarRows
      .map(r => ({
        name: r.producto.length > 35 ? r.producto.slice(0, 32) + "..." : r.producto,
        infracciones: infraCount[r.id] || 0,
        riesgo: r.riesgo,
      }))
      .filter(r => r.infracciones > 0)
      .sort((a, b) => b.infracciones - a.infracciones)
      .slice(0, 10);
  }, [radarRows, infraCount]);

  // Config form
  const [mapForm, setMapForm] = useState({ min: 0, max: 0, grupoId: 0 });
  const [saveVersion, setSaveVersion] = useState(0);
  useEffect(() => {
    if (selectedRow) setMapForm({ min: selectedRow.minP, max: selectedRow.maxP, grupoId: selectedRow.grupoId ?? 0 });
  }, [selectedProducto, saveVersion]);

  const [newGrupoName, setNewGrupoName] = useState("");
  const [newGrupoEmoji, setNewGrupoEmoji] = useState("📁");

  const [saving, setSaving] = useState(false);
  const [deletingRule, setDeletingRule] = useState<number | null>(null);
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [deletingGroup, setDeletingGroup] = useState<number | null>(null);
  const [confirmDeleteGroup, setConfirmDeleteGroup] = useState<number | null>(null);
  const [assigningLoading, setAssigningLoading] = useState<number | null>(null);

  const handleSaveConfig = async () => {
    if (!selectedRow) {
      toast("Seleccioná un producto primero", "error");
      return;
    }
    setSaving(true);
    try {
      console.log("[handleSaveConfig] saving for cazaId:", selectedRow.id, "grupoId:", mapForm.grupoId);
      const ruleRes = await api.upsertMonitorRule(selectedRow.id, {
        product_name: selectedRow.producto, product_url: selectedRow.url,
        source: "generic", min_price_allowed: mapForm.min, max_price_allowed: mapForm.max,
      });
      console.log("[handleSaveConfig] upsertMonitorRule result:", ruleRes);
      const groupRes = await api.assignMonitorGrupo(selectedRow.id, mapForm.grupoId || null);
      console.log("[handleSaveConfig] assignMonitorGrupo result:", groupRes);
      await loadData();
      if (ruleRes.error || groupRes.error) {
        toast(ruleRes.error || groupRes.error || "Error al guardar", "error");
      } else {
        toast("Configuración guardada", "success");
      }
    } catch (e) {
      toast("Error inesperado al guardar", "error");
    } finally {
      setSaveVersion(v => v + 1);
      setSaving(false);
    }
  };

  const handleDeleteRule = async (cazaId: number) => {
    setDeletingRule(cazaId);
    const res = await api.deleteMonitorRule(cazaId);
    setDeletingRule(null);
    if (res.error) {
      toast(res.error, "error");
      return;
    }
    await loadData();
    toast("Producto sacado del monitoreo", "success");
  };

  const handleCreateGrupo = async () => {
    if (!newGrupoName.trim()) return;
    setCreatingGroup(true);
    await api.createMonitorGrupo(newGrupoName.trim(), newGrupoEmoji);
    await loadData();
    setNewGrupoName("");
    setCreatingGroup(false);
    toast("Grupo creado", "success");
  };

  const handleDeleteGrupo = async (id: number) => {
    setDeletingGroup(id);
    setConfirmDeleteGroup(null);
    await api.deleteMonitorGrupo(id);
    await loadData();
    setDeletingGroup(null);
    toast("Grupo eliminado", "success");
  };

  const handleAssignGroup = async (cazaId: number, grupoId: number) => {
    setAssigningLoading(cazaId);
    const res = await api.assignMonitorGrupo(cazaId, grupoId || null);
    setAssigningLoading(null);
    if (res.error) {
      toast(res.error, "error");
    }
    await loadData();
  };

  if (loading) {
    return <PageTransition><div className="p-6 space-y-4"><SkeletonCard count={6} /></div></PageTransition>;
  }

  return (
    <PageTransition>
      <div className="p-4 md:p-8 space-y-14">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">📊 Monitor de Precios</h2>
            <p className="text-sm text-gray-500">Cumplimiento MAP en tiempo real</p>
          </div>
        </div>

        {cazas.length === 0 ? (
          <div className="text-center py-16 bg-gray-900/40 rounded-2xl" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
            <p className="text-4xl mb-3">📡</p>
            <p className="text-lg font-medium text-gray-300">No hay productos monitoreados</p>
            <p className="text-sm text-gray-500 mt-1">Creá una cacería desde Mis Rastreadores para empezar</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Productos", value: stats.total, color: "text-white", icon: "📦" },
                { label: "En cumplimiento", value: stats.enRango, color: "text-green-400", icon: "✅" },
                { label: "Violaciones", value: stats.violacion, color: stats.violacion > 0 ? "text-red-400" : "text-gray-500", icon: "🔴" },
                { label: "Alertas", value: stats.alerta, color: stats.alerta > 0 ? "text-yellow-400" : "text-gray-500", icon: "⚠️" },
              ].map(s => (
                <div key={s.label} className="bg-gray-900/60 rounded-xl p-4" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider">{s.label}</span>
                    <span className="text-sm">{s.icon}</span>
                  </div>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                </div>
              ))}
            </div>

            <div className="bg-gray-900/60 rounded-2xl p-4 md:p-6" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-300">📡 Radar de Precios</h3>
                <button onClick={async () => {
                  const rows = sorted.map(r => ({
                    Producto: r.producto, Precio: r.precio,
                    "Mín. MAP": r.minP, "Máx. MAP": r.maxP,
                    Riesgo: r.riesgo, Grupo: r.grupoNombre, ID: r.id,
                  }));
                  const res = await api.post("/api/export/sheets", { rows, sheet_name: "Radar Howlify" });
                  if (res.error) toast(res.error, "error");
                  else toast("Exportado a Google Sheets", "success");
                }} className="px-2.5 py-1.5 rounded-md text-xs font-medium bg-gray-800/40 text-gray-400 hover:text-gray-200 hover:bg-gray-700/50 transition-all border border-gray-700/30">
                  📤 Exportar
                </button>
              </div>
              <div className="flex gap-1 bg-gray-800/40 rounded-lg p-0.5 mb-5 w-fit">
                <button onClick={() => setMode("id")} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${mode === "id" ? "bg-red-500/20 text-red-400" : "text-gray-500 hover:text-gray-300"}`}>Individual</button>
                <button onClick={() => setMode("grupo")} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${mode === "grupo" ? "bg-red-500/20 text-red-400" : "text-gray-500 hover:text-gray-300"}`}>Por grupo</button>
              </div>

               <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-500 text-xs uppercase border-b border-gray-800/50">
                      <th className="py-3 pr-3"></th>
                      <th className="py-3 pr-4">Grupo</th>
                      <th className="py-3 pr-4">Riesgo</th>
                      <th className="py-3 pr-4">ID</th>
                      <th className="py-3 pr-4 text-left">Producto</th>
                      <th className="py-3 pr-4 text-right">Precio</th>
                      <th className="py-3 pr-4 text-right">Mín. MAP</th>
                      <th className="py-3 pr-4 text-right">Máximo</th>
                      <th className="py-3 pr-4 text-center">Estado</th>
                      <th className="py-3 pr-4 text-center">E</th>
                      <th className="py-3">Rango</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((row) => (
                      <tr key={row.id} onClick={() => setSelectedProducto(row.producto)}
                        className={`border-b border-gray-800/30 text-gray-300 hover:bg-gray-800/20 cursor-pointer transition-colors ${selectedProducto === row.producto ? "bg-red-500/5" : ""}`}>
                        <td className="py-3 pr-3 relative">
                          <button onClick={(e) => { 
                              e.stopPropagation(); 
                              console.log("📁 clicked, row.id:", row.id, "current grupoId:", row.grupoId);
                              setAssigningGroup(assigningGroup === row.id ? null : row.id); 
                            }}
                            className="text-xs cursor-pointer hover:scale-110 transition-transform" title="Asignar grupo">
                            {row.grupoColor.startsWith("#") ? "📁" : row.grupoColor}
                          </button>
                          {assigningGroup === row.id && (
                            <div className="absolute top-0 left-8 z-[9999] bg-gray-950 border border-red-500/50 rounded-xl p-2 shadow-2xl min-w-[160px]" onClick={(e) => e.stopPropagation()}>
                              <button onClick={() => { console.log("click sin grupo"); handleAssignGroup(row.id, 0); setAssigningGroup(null); }}
                                className="block w-full text-left px-3 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors">
                                — Sin grupo
                              </button>
                              {grupos.length === 0 && <p className="text-xs text-gray-500 px-3 py-1.5">(sin grupos)</p>}
                              {grupos.map(g => (
                                <button key={g.id} onClick={() => { console.log("click grupo", g.id, g.nombre); handleAssignGroup(row.id, g.id); setAssigningGroup(null); }}
                                  className="block w-full text-left px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors">
                                  {g.color} {g.nombre}
                                </button>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="py-3 pr-4 text-xs text-gray-500">{row.grupoNombre}</td>
                        <td className="py-3 pr-4 text-lg">{row.riesgo}</td>
                        <td className="py-3 pr-4 text-gray-500 text-xs">{row.id}</td>
                        <td className="py-3 pr-4 font-medium text-white max-w-[200px] truncate">{row.producto}</td>
                        <td className="py-3 pr-4 text-right tabular-nums">{row.precio > 0 ? `$${row.precio.toLocaleString()}` : "-"}</td>
                        <td className="py-3 pr-4 text-right tabular-nums text-red-400">{row.minP > 0 ? `$${row.minP.toLocaleString()}` : "-"}</td>
                        <td className="py-3 pr-4 text-right tabular-nums text-red-400">{row.maxP > 0 ? `$${row.maxP.toLocaleString()}` : "-"}</td>
                        <td className="py-3 pr-4 text-center">{row.riesgo === "⚪" ? <span className="text-gray-600">—</span> : <span className="text-lg">{row.riesgo}</span>}</td>
                        <td className="py-3 pr-4 text-center">
                          {row.tieneEvidencia
                            ? <button onClick={(e) => { e.stopPropagation(); setEvidenciaModal(String(row.id)); }} className="text-sm cursor-pointer hover:scale-125 transition-transform" title="Ver evidencia">📸</button>
                            : <span className="text-gray-600">—</span>}
                        </td>
                        <td className="py-3 w-24">
                          <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full transition-all ${row.riesgo === "🔴" ? "bg-red-500" : row.riesgo === "🟠" ? "bg-orange-500" : row.riesgo === "🟡" ? "bg-yellow-500" : row.riesgo === "🟢" ? "bg-green-500" : "bg-gray-600"}`}
                              style={{ width: `${row.progreso * 100}%` }} />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="md:hidden space-y-3">
                {sorted.map((row) => (
                  <div key={row.id} onClick={() => setSelectedProducto(row.producto)}
                    className={`bg-gray-800/30 rounded-xl p-4 border cursor-pointer transition-colors ${selectedProducto === row.producto ? "border-red-500/30 bg-red-500/10" : "border-gray-800/50"}`}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs text-gray-500">#{row.id}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{row.riesgo}</span>
                        {row.tieneEvidencia && <button onClick={(e) => { e.stopPropagation(); setEvidenciaModal(String(row.id)); }} className="text-sm hover:scale-125 transition-transform">📸</button>}
                      </div>
                    </div>
                    <p className="text-sm font-medium text-white truncate">{row.producto}</p>
                    <div className="flex items-center gap-2 mt-1.5 text-xs text-gray-400 flex-wrap">
                      <span className="tabular-nums">${row.precio.toLocaleString()}</span>
                      <span className="text-red-400 tabular-nums">MAP ${row.minP.toLocaleString()}-${row.maxP.toLocaleString()}</span>
                      <div className="relative">
                        <button onClick={(e) => { e.stopPropagation(); setAssigningGroup(assigningGroup === row.id ? null : row.id); }}
                          className="text-[10px] text-gray-500 hover:text-gray-300 hover:bg-gray-800/50 px-2 py-0.5 rounded transition-colors cursor-pointer">
                          {row.grupoId ? `${row.grupoColor} ${row.grupoNombre}` : "+ grupo"}
                        </button>
                        {assigningGroup === row.id && (
                          <div className="absolute bottom-6 left-0 z-50 bg-gray-900 border border-gray-700/50 rounded-xl p-2 shadow-2xl min-w-[140px]" onClick={(e) => e.stopPropagation()}>
                            <button onClick={() => { handleAssignGroup(row.id, 0); setAssigningGroup(null); }}
                              className="block w-full text-left px-3 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors">
                              — Sin grupo
                            </button>
                            {grupos.map(g => (
                              <button key={g.id} onClick={() => { handleAssignGroup(row.id, g.id); setAssigningGroup(null); }}
                                className="block w-full text-left px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors">
                                {g.color} {g.nombre}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="w-full h-1.5 mt-3 bg-gray-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${row.riesgo === "🔴" ? "bg-red-500" : row.riesgo === "🟠" ? "bg-orange-500" : row.riesgo === "🟡" ? "bg-yellow-500" : row.riesgo === "🟢" ? "bg-green-500" : "bg-gray-600"}`}
                        style={{ width: `${row.progreso * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-900/60 rounded-2xl p-4 md:p-6" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
                <h3 className="text-sm font-semibold text-gray-300 mb-4">🔧 Configurar producto</h3>
                <select value={selectedProducto || ""} onChange={e => setSelectedProducto(e.target.value || null)}
                  className="w-full mb-4 px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50">
                  <option value="">Seleccionar producto...</option>
                  {radarRows.map(r => <option key={r.id} value={r.producto}>{r.producto}</option>)}
                </select>
                {selectedRow && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { label: "Precio Actual", value: `$${selectedRow.precio.toLocaleString()}`, cls: "text-white" },
                        { label: "Estado", value: selectedRow.riesgo, cls: "text-lg" },
                        { label: "MAP Mínimo", value: `$${selectedRow.minP.toLocaleString()}`, cls: "text-red-400" },
                        { label: "MAP Máximo", value: `$${selectedRow.maxP.toLocaleString()}`, cls: "text-red-400" },
                      ].map(s => (
                        <div key={s.label} className="bg-gray-800/30 rounded-xl p-3 text-center">
                          <p className="text-[10px] text-gray-500 uppercase">{s.label}</p>
                          <p className={`text-sm font-bold ${s.cls}`}>{s.value}</p>
                        </div>
                      ))}
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-[10px] text-gray-400 ml-1 uppercase">Mín. MAP</label>
                        <input type="number" value={mapForm.min} onChange={e => setMapForm(f => ({ ...f, min: Number(e.target.value) }))}
                          className="w-full mt-1 px-3 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50" />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-400 ml-1 uppercase">Máx. MAP</label>
                        <input type="number" value={mapForm.max} onChange={e => setMapForm(f => ({ ...f, max: Number(e.target.value) }))}
                          className="w-full mt-1 px-3 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50" />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-400 ml-1 uppercase">Grupo</label>
                        <div className="flex gap-1.5 mt-1">
                          <select value={mapForm.grupoId} onChange={e => setMapForm(f => ({ ...f, grupoId: Number(e.target.value) }))}
                            className="flex-1 px-3 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50">
                            <option value={0}>Sin Grupo</option>
                            {grupos.map(g => <option key={g.id} value={g.id}>{g.color} {g.nombre}</option>)}
                          </select>
                          <button onClick={() => { if (selectedRow) handleAssignGroup(selectedRow.id, mapForm.grupoId); }}
                            disabled={assigningLoading === selectedRow?.id}
                            className="px-4 py-2.5 bg-red-500/20 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/30 transition-all border border-red-500/20 shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Asignar grupo">
                            {assigningLoading === selectedRow?.id ? "⏳" : "Asignar"}
                          </button>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={handleSaveConfig} disabled={saving}
                        className="flex-1 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg font-semibold text-sm hover:from-red-600 hover:to-red-700 transition-all shadow-lg shadow-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed">
                        {saving ? "⏳ Guardando..." : "💾 Guardar Cambios"}
                      </button>
                      <button onClick={() => handleDeleteRule(selectedRow.id)} disabled={deletingRule === selectedRow.id}
                        className="px-4 py-2.5 bg-red-900/20 text-red-400 rounded-lg text-xs font-medium hover:bg-red-900/40 transition-all border border-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                        title="Sacar del monitoreo">
                        {deletingRule === selectedRow.id ? "⏳" : "🗑️"}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-gray-900/60 rounded-2xl p-4 md:p-6" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
                <h3 className="text-sm font-semibold text-gray-300 mb-4">⚙️ Grupos</h3>
                <div className="space-y-4">
                  <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-800/50">
                    <p className="text-xs font-medium text-gray-400 mb-3">Nuevo grupo</p>
                    <input value={newGrupoName} onChange={e => setNewGrupoName(e.target.value)} placeholder="Nombre"
                      className="w-full mb-3 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white placeholder-gray-600 text-sm focus:outline-none focus:border-red-500/50" />
                    <div className="flex gap-1.5 flex-wrap mb-3">
                      {EMOJIS.slice(0, 8).map(e => (
                        <button key={e} onClick={() => setNewGrupoEmoji(e)}
                          className={`w-8 h-8 rounded text-sm flex items-center justify-center transition-all ${newGrupoEmoji === e ? "bg-red-500/20 border border-red-500/30" : "bg-gray-700/30 border border-transparent hover:bg-gray-700/50"}`}>{e}</button>
                      ))}
                    </div>
                    <button onClick={handleCreateGrupo} disabled={creatingGroup}
                      className="w-full py-2 bg-red-500/10 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/20 transition-all border border-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed">
                      {creatingGroup ? "⏳ Creando..." : "+ Crear"}
                    </button>
                  </div>
                  {grupos.length > 0 && (
                    <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-800/50">
                      <p className="text-xs font-medium text-gray-400 mb-3">Eliminar grupo</p>
                      {confirmDeleteGroup ? (
                        <div className="space-y-2">
                          <p className="text-xs text-yellow-400">¿Eliminar "{gruposMap.get(confirmDeleteGroup)?.nombre}"?</p>
                          <div className="flex gap-2">
                            <button onClick={() => { handleDeleteGrupo(confirmDeleteGroup); }}
                              disabled={deletingGroup === confirmDeleteGroup}
                              className="flex-1 py-2 bg-red-500/20 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/30 transition-all border border-red-500/30 disabled:opacity-50">
                              {deletingGroup === confirmDeleteGroup ? "⏳" : "Eliminar"}
                            </button>
                            <button onClick={() => setConfirmDeleteGroup(null)}
                              className="flex-1 py-2 bg-gray-800/50 text-gray-400 rounded-lg text-xs hover:bg-gray-700/50 transition-all border border-gray-700/50">
                              Cancelar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <select value="" onChange={e => { if (e.target.value) setConfirmDeleteGroup(Number(e.target.value)); }}
                          className="w-full px-3 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50">
                          <option value="">Seleccionar...</option>
                          {grupos.map(g => <option key={g.id} value={g.id}>{g.color} {g.nombre}</option>)}
                        </select>
                      )}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {grupos.map(g => (
                      <span key={g.id} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-800/40 rounded-lg text-xs text-gray-300 border border-gray-700/50">
                        {g.color} {g.nombre}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gray-900/60 rounded-2xl p-4 md:p-6" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
              <div className="flex items-center gap-1.5 mb-5 bg-gray-800/40 rounded-lg p-1 w-fit">
                {([
                  { key: "general" as ChartTab, label: "Visión General", icon: "📊" },
                  { key: "historico" as ChartTab, label: "Histórico", icon: "📈" },
                  { key: "alertas" as ChartTab, label: "Alertas", icon: "🚨" },
                  { key: "ranking" as ChartTab, label: "Ranking", icon: "🏆" },
                ]).map(t => (
                  <button key={t.key} onClick={() => setChartTab(t.key)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${chartTab === t.key ? "bg-red-500/20 text-red-400" : "text-gray-500 hover:text-gray-300"}`}>
                    {t.icon} {t.label}
                  </button>
                ))}
              </div>

              {chartTab === "general" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-1.5">
                      Estado general de precios
                      <InfoButton description="Muestra la proporción de productos en cada estado de cumplimiento. Los segmentos representan productos en rango (verde), cerca del límite (amarillo), en el límite (naranja), fuera de rango (rojo) y sin datos de precio (gris)." />
                    </h4>
                    <ResponsiveContainer width="100%" height={240}>
                      <PieChart>
                        <Pie data={complianceData.filter(d => d.value > 0)} cx="50%" cy="50%" innerRadius={55} outerRadius={95}
                          paddingAngle={3} dataKey="value" stroke="none">
                          {complianceData.filter(d => d.value > 0).map((entry, i) => (
                            <Cell key={i} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-1.5">
                      Cumplimiento
                      <InfoButton description="Cantidad de productos en cada categoría de cumplimiento. Permite ver rápidamente cuántos productos están dentro del rango MAP permitido, cuántos están en alerta y cuántos en violación." />
                    </h4>
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={complianceData.filter(d => d.value > 0)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                        <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                        <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
                        <Tooltip />
                        <Bar dataKey="value" stroke="none" radius={[4, 4, 0, 0]}>
                          {complianceData.filter(d => d.value > 0).map((entry, i) => (
                            <Cell key={i} fill={entry.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {chartTab === "historico" && (
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <h4 className="text-sm font-semibold text-gray-300 flex items-center gap-1.5">
                      Evolución de precios
                      <InfoButton description="Evolución del precio de un producto a lo largo del tiempo. Las líneas punteadas verdes marcan los límites MAP mínimo y máximo. Seleccioná un producto en el menú desplegable para ver su histórico." />
                    </h4>
                    <select value={selectedProducto || ""} onChange={e => setSelectedProducto(e.target.value || null)}
                      className="ml-auto px-3 py-1.5 bg-gray-800/50 border border-gray-700/50 rounded-lg text-xs text-white focus:outline-none focus:border-red-500/50">
                      <option value="">Seleccionar producto...</option>
                      {radarRows.map(r => <option key={r.id} value={r.producto}>{r.producto}</option>)}
                    </select>
                  </div>
                  {selectedRow && selectedHistory.length > 1 ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={selectedHistory}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                        <XAxis dataKey="checked_at" tick={{ fill: "#9ca3af", fontSize: 10 }}
                          tickFormatter={(v) => new Date(v).toLocaleDateString()} />
                        <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
                        <Tooltip />
                        <Line type="monotone" dataKey="price" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
                        {selectedRow.minP > 0 && (
                          <Line type="monotone" dataKey={() => selectedRow.minP} stroke="#22c55e" strokeWidth={1}
                            strokeDasharray="5 5" name="MAP mín" data={selectedHistory.map(h => ({ ...h, price: selectedRow.minP }))} />
                        )}
                        {selectedRow.maxP > 0 && (
                          <Line type="monotone" dataKey={() => selectedRow.maxP} stroke="#22c55e" strokeWidth={1}
                            strokeDasharray="5 5" name="MAP máx" data={selectedHistory.map(h => ({ ...h, price: selectedRow.maxP }))} />
                        )}
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="text-center py-12 text-gray-500 text-sm">
                      {!selectedProducto ? "Seleccioná un producto para ver su histórico" : "Sin datos de historial"}
                    </div>
                  )}
                </div>
              )}

              {chartTab === "alertas" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-1.5">
                      Precio vs rango MAP
                      <InfoButton description="Cada punto representa una medición de precio del producto seleccionado. Los puntos verdes están dentro del rango MAP, los rojos están fuera. Permite identificar cuándo y con qué frecuencia un producto sale de los límites permitidos." />
                    </h4>
                    {selectedRow && selectedHistory.length > 1 ? (
                      <ResponsiveContainer width="100%" height={280}>
                        <ScatterChart>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                          <XAxis dataKey="checked_at" tick={{ fill: "#9ca3af", fontSize: 10 }}
                            tickFormatter={(v) => new Date(v).toLocaleDateString()} />
                          <YAxis dataKey="price" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                          <Tooltip />
                          <Scatter data={selectedHistory.map(h => ({
                            ...h,
                            fill: (selectedRow.minP > 0 && h.price < selectedRow.minP) ? COLORS.rojo : COLORS.verde,
                          }))} stroke="none" shape="circle" />
                        </ScatterChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="text-center py-12 text-gray-500 text-sm">Seleccioná un producto con historial</div>
                    )}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-1.5">
                      Frecuencia de infracciones
                      <InfoButton description="Cantidad de infracciones registradas por día. Una infracción ocurre cuando el precio de un producto está fuera del rango MAP permitido. Picos altos pueden indicar problemas generalizados de cumplimiento." />
                    </h4>
                    {infracciones.length > 0 ? (
                      <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={Object.entries(
                          infracciones.reduce((acc: Record<string, number>, i) => {
                            const d = i.fecha ? new Date(i.fecha).toLocaleDateString() : "sin fecha";
                            acc[d] = (acc[d] || 0) + 1;
                            return acc;
                          }, {})
                        ).slice(-20).map(([fecha, count]) => ({ fecha, count }))}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                          <XAxis dataKey="fecha" tick={{ fill: "#9ca3af", fontSize: 9 }} />
                          <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
                          <Tooltip />
                          <Bar dataKey="count" fill={COLORS.rojo} radius={[2, 2, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="text-center py-12 text-gray-500 text-sm">Sin infracciones registradas</div>
                    )}
                  </div>
                </div>
              )}

              {chartTab === "ranking" && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-1.5">
                    Productos más problemáticos
                    <InfoButton description="Ranking de los 10 productos con más infracciones acumuladas. Ayuda a identificar rápidamente qué productos necesitan atención urgente. El color indica el nivel de riesgo actual de cada producto." />
                  </h4>
                  {rankingData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={Math.max(200, rankingData.length * 35)}>
                      <BarChart data={rankingData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                        <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                        <YAxis dataKey="name" type="category" tick={{ fill: "#9ca3af", fontSize: 11 }} width={200} />
                        <Tooltip />
                        <Bar dataKey="infracciones" stroke="none" radius={[0, 4, 4, 0]}>
                          {rankingData.map((entry, i) => (
                            <Cell key={i} fill={entry.riesgo === "🔴" ? COLORS.rojo : entry.riesgo === "🟡" ? COLORS.amarillo : COLORS.naranja} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="text-center py-12 text-gray-500 text-sm">No hay infracciones para ranking</div>
                  )}
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 bg-gray-900/40 rounded-xl px-5 py-3" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
              <span className="text-gray-400 font-medium">Leyenda:</span>
              {(["🟢", "🟡", "🟠", "🔴", "⚪"] as RiskColor[]).map(r => (
                <span key={r} className="flex items-center gap-1">{r} {RIESGO_LABEL[r]}</span>
              ))}
            </div>
          </>
        )}

        {evidenciaModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={() => setEvidenciaModal(null)}>
            <div className="relative max-w-3xl max-h-[90vh] mx-4" onClick={(e) => e.stopPropagation()}>
              <div className="absolute -top-3 -right-3 flex gap-2 z-10">
                <a href={`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/monitor/evidencia/${evidenciaModal}?token=${localStorage.getItem("token") || ""}`} download={`evidencia_${evidenciaModal}.png`} className="w-8 h-8 bg-gray-900 rounded-full border border-gray-700 text-gray-400 hover:text-white flex items-center justify-center text-sm">⬇</a>
                <button onClick={() => setEvidenciaModal(null)} className="w-8 h-8 bg-gray-900 rounded-full border border-gray-700 text-gray-400 hover:text-white flex items-center justify-center">✕</button>
              </div>
              <img src={`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/monitor/evidencia/${evidenciaModal}?token=${localStorage.getItem("token") || ""}`} alt="Evidencia"
                className="max-w-full max-h-[90vh] rounded-2xl border border-gray-700/50 shadow-2xl" />
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  );
}
