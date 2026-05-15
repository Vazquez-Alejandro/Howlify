import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Caza } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import PageTransition from "../components/PageTransition";
import CazaCard from "../components/CazaCard";
import SkeletonCard from "../components/SkeletonCard";
import Logo from "../components/Logo";
import MonitorPage from "./MonitorPage";

type View = "rastreadores" | "perfil" | "admin" | "monitor";

const PLAN_INFO: Record<string, { label: string; max: number }> = {
  starter: { label: "Starter", max: 5 },
  pro: { label: "Pro", max: 15 },
  business_reseller: { label: "Business Reseller", max: 40 },
  business_monitor: { label: "Business Monitor", max: 100 },
};

export default function DashboardPage() {
  const [cazas, setCazas] = useState<Caza[]>([]);
  const [loading, setLoading] = useState(false);
  const [hunting, setHunting] = useState<Record<string, boolean>>({});
  const [huntAllLoading, setHuntAllLoading] = useState(false);
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [view, setView] = useState<View>("rastreadores");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profile, setProfile] = useState<{ role?: string; plan?: string } | null>(null);
  const [simulatedPlan, setSimulatedPlan] = useState("starter");
  const [users, setUsers] = useState<Record<string, unknown>[]>([]);

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

  useEffect(() => {
    api.getProfile().then((res) => {
      console.log("[profile] response:", res);
      if (res.data?.profile) {
        setProfile(res.data.profile);
      } else if (res.error) {
        console.warn("[profile] error:", res.error);
      }
    });
  }, []);

  const isAdmin = profile?.role === "admin";

  const loadUsers = async () => {
    const res = await api.adminUsers();
    if (res.data?.users) setUsers(res.data.users);
  };

  useEffect(() => {
    if (isAdmin) loadUsers();
  }, [isAdmin]);

  const handleHuntAll = async () => {
    setHuntAllLoading(true);
    toast("Olfateando todas las cacerías...", "info");
    await api.huntAll();
    setHuntAllLoading(false);
    await loadCazas();
    toast("Todas las cacerías actualizadas", "success");
  };

  const handleDelete = async (id: number) => {
    await api.deleteCaza(id);
    await loadCazas();
  };

  const activeCazas = cazas.filter((c) => c.estado === "active" || !c.estado).length;
  const alertsCount = cazas.filter((c) => c.last_price && c.last_price <= c.precio_max).length;

  const effectivePlan = isAdmin ? simulatedPlan : (profile?.plan || "starter");
  const planInfo = PLAN_INFO[effectivePlan] || PLAN_INFO.starter;
  const maxCazas = planInfo.max;
  const planName = planInfo.label;

  const menuItems: { key: View; label: string; icon: string }[] = [
    { key: "rastreadores", label: "Mis Rastreadores", icon: "🐺" },
    ...(effectivePlan === "business_monitor" || isAdmin ? [{ key: "monitor" as View, label: "Monitor", icon: "📊" }] : []),
    ...(isAdmin ? [{ key: "admin" as View, label: "Panel Admin", icon: "🛠️" }] : []),
    { key: "perfil", label: "Mi Perfil", icon: "👤" },
  ];

  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-950 flex">
        {/* Mobile overlay */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setSidebarOpen(false)} />
        )}

        {/* Sidebar */}
        <aside className={`fixed lg:sticky top-0 left-0 z-50 h-screen w-64 bg-gray-900/95 backdrop-blur-xl border-r border-gray-800/50 flex flex-col transition-transform duration-200 lg:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
          <div className="p-5 border-b border-gray-800/50">
            <div className="flex items-center gap-3">
              <Logo size="sm" />
              <div>
                <h2 className="font-bold text-white text-sm">Howlify</h2>
                <p className="text-[10px] text-gray-500">Plan {planName}</p>
              </div>
            </div>
          </div>
          <nav className="flex-1 p-3 space-y-1">
            {menuItems.map((item) => (
              <button
                key={item.key}
                onClick={() => { setView(item.key); setSidebarOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  view === item.key
                    ? "bg-red-500/10 text-red-400 border border-red-500/20"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-transparent"
                }`}
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </nav>
          <div className="p-3 border-t border-gray-800/50">
            <div className="px-3 py-2 text-xs text-gray-500 truncate">{user?.email}</div>
            <button
              onClick={() => { logout(); navigate("/"); }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-red-400 rounded-xl hover:bg-red-500/5 transition-all"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
              Cerrar sesión
            </button>
          </div>
        </aside>

        {/* Main content */}
        <div className="flex-1 flex flex-col min-h-screen">
          {/* Top bar */}
          <header className="sticky top-0 z-30 bg-gray-950/80 backdrop-blur-xl border-b border-gray-800/50">
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-gray-400 hover:text-white">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
                </button>
                <h1 className="text-lg font-bold text-white">
                  {view === "rastreadores" ? "Mis Cacerías" : view === "monitor" ? "Monitor" : view === "admin" ? "Panel Admin" : "Mi Perfil"}
                </h1>
              </div>
              {view === "rastreadores" && cazas.length > 0 && (
                <button
                  onClick={handleHuntAll}
                  disabled={huntAllLoading}
                  className="px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-medium text-sm hover:from-red-600 hover:to-red-700 transition-all disabled:opacity-50 shadow-lg shadow-red-500/20 flex items-center gap-2"
                >
                  {huntAllLoading ? (
                    <><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Olfateando...</>
                  ) : "🔎 Olfatear todas"}
                </button>
              )}
            </div>
            {/* Stats bar */}
            {view === "rastreadores" && (
              <div className="px-4 pb-3 grid grid-cols-3 gap-2">
                <div className="bg-gray-900/60 rounded-xl border border-gray-800/50 px-3 py-2.5">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">Cacerías</p>
                  <p className="text-lg font-bold text-white mt-0.5">{cazas.length} / {maxCazas}</p>
                </div>
                <div className="bg-gray-900/60 rounded-xl border border-gray-800/50 px-3 py-2.5">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">Activas</p>
                  <p className="text-lg font-bold text-green-400 mt-0.5">{activeCazas}</p>
                </div>
                <div className="bg-gray-900/60 rounded-xl border border-gray-800/50 px-3 py-2.5">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">Alertas</p>
                  <p className={`text-lg font-bold mt-0.5 ${alertsCount > 0 ? "text-red-400" : "text-gray-500"}`}>{alertsCount}</p>
                </div>
              </div>
            )}
          </header>

          {/* Rastreadores view */}
          {view === "rastreadores" && (
            <main className="flex-1 px-4 py-5 max-w-3xl mx-auto w-full">
              {loading && <SkeletonCard count={3} />}

              {!loading && cazas.length === 0 && (
                <div className="text-center py-16">
                  <p className="text-lg font-medium text-gray-300">No tenés cacerías activas</p>
                  <p className="text-sm text-gray-500 mt-1">Agregá una desde el panel de abajo</p>
                </div>
              )}

              <div className="space-y-3">
                {cazas.map((c) => (
                  <CazaCard
                    key={c.id}
                    caza={c}
                    onHunt={() => handleHunt(c.id)}
                    onDelete={() => handleDelete(c.id)}
                    onUpdate={() => loadCazas()}
                    hunting={!!hunting[String(c.id)]}
                  />
                ))}
              </div>

              <NewCazaForm onCreated={() => { loadCazas(); toast("Cacería creada", "success"); }} />
            </main>
          )}

          {/* Perfil view */}
          {view === "perfil" && (
            <main className="flex-1 px-4 py-5 max-w-xl mx-auto w-full">
              <div className="bg-gray-900/60 rounded-2xl border border-gray-800/50 p-6 space-y-5">
                <div className="flex items-center gap-4">
                  <Logo size="md" />
                  <div>
                    <h3 className="text-lg font-bold text-white">{user?.email?.split("@")[0] || "Usuario"}</h3>
                    <p className="text-sm text-gray-400">{user?.email}</p>
                  </div>
                </div>
                <div className="h-px bg-gray-800/50" />
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Plan</span>
                    <span className="text-sm font-medium text-white">{planName}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Cacerías</span>
                    <span className="text-sm font-medium text-white">{cazas.length} / {maxCazas}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Alertas activas</span>
                    <span className={`text-sm font-medium ${alertsCount > 0 ? "text-red-400" : "text-gray-500"}`}>{alertsCount}</span>
                  </div>
                </div>
                <button
                  onClick={() => { logout(); navigate("/"); }}
                  className="w-full py-2.5 bg-red-500/10 text-red-400 rounded-xl font-medium hover:bg-red-500/20 transition-all border border-red-500/20"
                >
                  Cerrar sesión
                </button>
              </div>
            </main>
          )}

          {/* Monitor view */}
          {view === "monitor" && <MonitorPage />}

          {/* Admin view */}
          {view === "admin" && (
            <main className="flex-1 px-4 py-5 max-w-4xl mx-auto w-full">
              <h2 className="text-xl font-bold text-white mb-4">🛠️ Panel de Admin</h2>

              <div className="bg-gray-900/60 rounded-2xl border border-gray-800/50 p-5 mb-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">Simular vista de plan</h3>
                <div className="flex flex-wrap gap-2">
                  {["starter", "pro", "business_reseller", "business_monitor"].map((p) => (
                    <button
                      key={p}
                      onClick={() => setSimulatedPlan(p)}
                      className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all ${
                        simulatedPlan === p
                          ? "bg-red-500/15 text-red-400 border-red-500/30"
                          : "bg-gray-800/30 text-gray-400 border-gray-700/50 hover:border-gray-600"
                      }`}
                    >
                      {PLAN_INFO[p].label}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  Viendo como: <span className="text-red-400 font-medium">{planName}</span>
                  {" · "}
                  Límite: <span className="text-white font-medium">{maxCazas} cacerías</span>
                </p>
              </div>

              <div className="bg-gray-900/60 rounded-2xl border border-gray-800/50 p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">👥 Usuarios (últimos 30)</h3>
                {users.length === 0 ? (
                  <p className="text-sm text-gray-500">No hay usuarios.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead>
                        <tr className="text-gray-500 text-xs uppercase border-b border-gray-800/50">
                          <th className="py-2 pr-3">Email</th>
                          <th className="py-2 pr-3">Plan</th>
                          <th className="py-2 pr-3">Rol</th>
                          <th className="py-2">Registro</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.slice(0, 30).map((u: any, i) => (
                          <tr key={i} className="border-b border-gray-800/30 text-gray-300">
                            <td className="py-2 pr-3 truncate max-w-[200px]">{u.email || "-"}</td>
                            <td className="py-2 pr-3">{u.plan || "-"}</td>
                            <td className="py-2 pr-3">{u.role || "user"}</td>
                            <td className="py-2">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </main>
          )}

          {/* Footer */}
          <footer className="border-t border-gray-800/50 px-4 py-4 text-center text-xs text-gray-600">
            Howlify 🐺 | La manada cazando... &middot; © 2026
          </footer>
        </div>
      </div>
    </PageTransition>
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

  if (!open) {
    return (
      <div className="mt-8">
        <button
          onClick={() => setOpen(true)}
          className="w-full py-4 border-2 border-dashed border-gray-700/50 rounded-2xl text-gray-500 hover:border-gray-500 hover:text-gray-300 transition-all flex items-center justify-center gap-2 group"
        >
          <span className="text-lg group-hover:scale-110 transition-transform">+</span>
          <span className="font-medium">Nueva Cacería</span>
        </button>
      </div>
    );
  }

  return (
    <div className="mt-8 relative group">
      <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500 to-red-700 rounded-2xl blur opacity-15" />
      <form onSubmit={handleSubmit} className="relative bg-gray-900/80 backdrop-blur-xl rounded-2xl p-6 border border-gray-800/50 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Configurar nueva cacería</h3>
          <button type="button" onClick={() => setOpen(false)} className="text-gray-500 hover:text-gray-300 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="flex gap-2 p-1 bg-gray-800/30 rounded-xl border border-gray-700/50">
          {["🛒 Producto", "✈️ Vuelo", "🏠 Alojamiento"].map((t) => (
            <button key={t} type="button" className="flex-1 py-2 px-3 rounded-lg text-xs font-medium bg-red-500/20 text-red-300 shadow-sm">{t}</button>
          ))}
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Nombre / Keyword</label>
          <input type="text" placeholder="Ej: Fernet Branca" value={form.keyword}
            onChange={(e) => setForm({ ...form, keyword: e.target.value })}
            className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all" required />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">URL de la tienda</label>
          <input type="url" placeholder="https://www.carrefour.com.ar/" value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
            className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all" required />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Precio Máximo</label>
            <input type="number" value={form.precio_max}
              onChange={(e) => setForm({ ...form, precio_max: Number(e.target.value) })}
              className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all" />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Frecuencia</label>
            <select value={form.frecuencia} onChange={(e) => setForm({ ...form, frecuencia: e.target.value })}
              className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all">
              <option value="1 h">Cada 1 hora</option>
              <option value="2 h">Cada 2 horas</option>
              <option value="4 h">Cada 4 horas</option>
              <option value="12 h">Cada 12 horas</option>
            </select>
          </div>
        </div>
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={loading}
            className="flex-1 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold hover:from-red-600 hover:to-red-700 transition-all disabled:opacity-50 shadow-lg shadow-red-500/20">
            {loading ? "Creando..." : "Lanzar 🐺"}
          </button>
          <button type="button" onClick={() => setOpen(false)}
            className="px-6 py-2.5 bg-gray-800/50 text-gray-400 rounded-xl hover:bg-gray-700/50 hover:text-gray-200 transition-all border border-gray-700/50">
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
}
