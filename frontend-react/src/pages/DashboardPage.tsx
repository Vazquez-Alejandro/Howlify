import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Caza } from "../api/client";
import { useAuth } from "../context/AuthContext";
import CazaCard from "../components/CazaCard";

export default function DashboardPage() {
  const [cazas, setCazas] = useState<Caza[]>([]);
  const [loading, setLoading] = useState(false);
  const [hunting, setHunting] = useState<Record<string, boolean>>({});
  const [huntAllLoading, setHuntAllLoading] = useState(false);
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const loadCazas = async () => {
    setLoading(true);
    const res = await api.listCazas();
    if (res.data) setCazas(res.data.cazas);
    setLoading(false);
  };

  const handleHunt = async (id: number) => {
    const key = String(id);
    setHunting((prev) => ({ ...prev, [key]: true }));
    await api.huntSingle(id);
    setHunting((prev) => ({ ...prev, [key]: false }));
    await loadCazas();
  };

  useEffect(() => { loadCazas(); }, []);

  const handleHuntAll = async () => {
    setHuntAllLoading(true);
    await api.huntAll();
    setHuntAllLoading(false);
    await loadCazas();
  };

  const handleDelete = async (id: number) => {
    await api.deleteCaza(id);
    await loadCazas();
  };

  const activeCazas = cazas.filter((c) => c.estado === "active" || !c.estado).length;
  const alertsCount = cazas.filter((c) => c.last_price && c.last_price <= c.precio_max).length;

  return (
    <div className="min-h-screen bg-gray-950">
      <header className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-xl border-b border-gray-800/50">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-red-500 to-red-700 shadow-lg shadow-red-500/20">
              <span className="text-lg">🐺</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white leading-tight">Howlify</h1>
              <p className="text-xs text-gray-500">Panel de Control</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400 hidden sm:block">{user?.email}</span>
            <button
              onClick={() => { logout(); navigate("/"); }}
              className="px-3 py-1.5 text-sm bg-gray-800/50 text-gray-400 rounded-xl hover:bg-gray-700/50 hover:text-gray-200 transition-all border border-gray-700/50"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
          <div className="bg-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-800/50 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">Cacerías</p>
            <p className="text-2xl font-bold text-white mt-1">{cazas.length}</p>
          </div>
          <div className="bg-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-800/50 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">Activas</p>
            <p className="text-2xl font-bold text-green-400 mt-1">{activeCazas}</p>
          </div>
          <div className="bg-gray-900/60 backdrop-blur-sm rounded-xl border border-gray-800/50 p-4 col-span-2 sm:col-span-1">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">Alertas</p>
            <p className={`text-2xl font-bold mt-1 ${alertsCount > 0 ? "text-red-400" : "text-gray-500"}`}>{alertsCount}</p>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">Mis Cacerías</h2>
          <button
            onClick={handleHuntAll}
            disabled={huntAllLoading || cazas.length === 0}
            className="px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-medium text-sm hover:from-red-600 hover:to-red-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-red-500/20 hover:shadow-red-500/30 flex items-center gap-2"
          >
            {huntAllLoading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                Olfateando...
              </>
            ) : (
              <>Olfatear todas</>
            )}
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16">
            <svg className="animate-spin h-8 w-8 text-red-500" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
          </div>
        )}

        {!loading && cazas.length === 0 && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gray-900/60 border border-gray-800/50 mb-4">
              <span className="text-3xl">🐺</span>
            </div>
            <p className="text-lg font-medium text-gray-300">No tenés cacerías activas</p>
            <p className="text-sm text-gray-500 mt-1">Agregá una desde el botón de abajo</p>
          </div>
        )}

        <div className="space-y-3">
          {cazas.map((c) => (
            <CazaCard
              key={c.id}
              caza={c}
              onHunt={() => handleHunt(c.id)}
              onDelete={() => handleDelete(c.id)}
              hunting={!!hunting[String(c.id)]}
            />
          ))}
        </div>

        <NewCazaForm onCreated={loadCazas} />
      </main>
    </div>
  );
}

function NewCazaForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ keyword: "", url: "", precio_max: 50000, frecuencia: "1 h" });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await api.createCaza(form);
    setLoading(false);
    setOpen(false);
    setForm({ keyword: "", url: "", precio_max: 50000, frecuencia: "1 h" });
    onCreated();
  };

  return (
    <div className="mt-8">
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="w-full py-4 border-2 border-dashed border-gray-700/50 rounded-2xl text-gray-500 hover:border-gray-500 hover:text-gray-300 transition-all duration-200 flex items-center justify-center gap-2 group"
        >
          <span className="text-lg group-hover:scale-110 transition-transform">+</span>
          <span className="font-medium">Nueva Cacería</span>
        </button>
      ) : (
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500 to-red-700 rounded-2xl blur opacity-15" />
          <form onSubmit={handleSubmit} className="relative bg-gray-900/80 backdrop-blur-xl rounded-2xl p-6 border border-gray-800/50 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Configurar nueva cacería</h3>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-gray-500 hover:text-gray-300 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Producto / Keyword</label>
              <input
                type="text" placeholder="Ej: Fernet Branca" value={form.keyword}
                onChange={(e) => setForm({ ...form, keyword: e.target.value })}
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">URL de la tienda</label>
              <input
                type="url" placeholder="https://www.carrefour.com.ar/fernett" value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Precio Máximo</label>
                <input
                  type="number" placeholder="50000" value={form.precio_max}
                  onChange={(e) => setForm({ ...form, precio_max: Number(e.target.value) })}
                  className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Frecuencia</label>
                <select
                  value={form.frecuencia}
                  onChange={(e) => setForm({ ...form, frecuencia: e.target.value })}
                  className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all"
                >
                  <option value="1 h">Cada 1 hora</option>
                  <option value="2 h">Cada 2 horas</option>
                  <option value="4 h">Cada 4 horas</option>
                  <option value="12 h">Cada 12 horas</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="submit" disabled={loading}
                className="flex-1 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold hover:from-red-600 hover:to-red-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-red-500/20 hover:shadow-red-500/30"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                    Creando...
                  </span>
                ) : "Lanzar 🐺"}
              </button>
              <button
                type="button" onClick={() => setOpen(false)}
                className="px-6 py-2.5 bg-gray-800/50 text-gray-400 rounded-xl hover:bg-gray-700/50 hover:text-gray-200 transition-all border border-gray-700/50"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
