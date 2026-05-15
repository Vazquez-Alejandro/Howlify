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
  const { logout, user } =   useAuth();
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

  return (
    <div className="min-h-screen bg-gray-950">
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🐺</span>
          <h1 className="text-xl font-bold text-white">Howlify</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">{user?.email}</span>
          <button
            onClick={() => { logout(); navigate("/"); }}
            className="px-4 py-1.5 text-sm bg-gray-800 text-gray-300 rounded-xl hover:bg-gray-700 transition"
          >
            Salir
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">Mis Cacerías</h2>
          <button
            onClick={handleHuntAll}
            disabled={huntAllLoading || cazas.length === 0}
            className="px-5 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-medium hover:from-red-600 hover:to-red-700 transition disabled:opacity-50"
          >
            {huntAllLoading ? "Olfateando..." : "🔎 Olfatear todas"}
          </button>
        </div>

        {loading && <p className="text-gray-400">Cargando...</p>}

        {!loading && cazas.length === 0 && (
          <div className="text-center py-16 text-gray-500">
            <p className="text-6xl mb-4">🐺</p>
            <p className="text-lg">No tenés cacerías activas</p>
            <p className="text-sm mt-2">Agregá una desde el botón de abajo</p>
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
          className="w-full py-3 border-2 border-dashed border-gray-700 rounded-2xl text-gray-400 hover:border-gray-500 hover:text-gray-300 transition"
        >
          + Nueva Cacería
        </button>
      ) : (
        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-6 border border-gray-800 space-y-4">
          <h3 className="text-lg font-semibold text-white">Configurar nueva cacería</h3>
          <input
            type="text" placeholder="Nombre / Etiqueta" value={form.keyword}
            onChange={(e) => setForm({ ...form, keyword: e.target.value })}
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
            required
          />
          <input
            type="url" placeholder="URL del producto" value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
            required
          />
          <div className="flex gap-4">
            <input
              type="number" placeholder="Precio Máximo" value={form.precio_max}
              onChange={(e) => setForm({ ...form, precio_max: Number(e.target.value) })}
              className="flex-1 px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
            />
            <select
              value={form.frecuencia}
              onChange={(e) => setForm({ ...form, frecuencia: e.target.value })}
              className="px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-red-500"
            >
              <option value="1 h">1 h</option>
              <option value="2 h">2 h</option>
              <option value="4 h">4 h</option>
              <option value="12 h">12 h</option>
            </select>
          </div>
          <div className="flex gap-3">
            <button
              type="submit" disabled={loading}
              className="flex-1 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-medium hover:from-red-600 hover:to-red-700 transition disabled:opacity-50"
            >
              {loading ? "Creando..." : "Lanzar 🐺"}
            </button>
            <button
              type="button" onClick={() => setOpen(false)}
              className="px-6 py-2.5 bg-gray-800 text-gray-300 rounded-xl hover:bg-gray-700 transition"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
