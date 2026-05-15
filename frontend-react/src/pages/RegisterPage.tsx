import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";

const plans = [
  { value: "starter", label: "Starter", price: "USD 9/mes", desc: "Hasta 5 cacerías", features: ["5 cacerías activas", "C/1 hora o más", "Alertas email", "Tiendas ML + genéricas"] },
  { value: "pro", label: "Pro", price: "USD 15/mes", desc: "Cacerías ilimitadas", features: ["15 cacerías activas", "C/15 min o más", "Alertas WhatsApp", "Export CSV"] },
  { value: "business_reseller", label: "Business Reseller", price: "USD 39/mes", desc: "Para revendedores", features: ["40 cacerías activas", "Dashboard empresa", "Multi-tienda por cacería", "Reporte diario"] },
  { value: "business_monitor", label: "Business Monitor", price: "USD 79/mes", desc: "Monitoreo total", features: ["100 cacerías activas", "Rankings de negocio", "Dashboard empresa completo", "Soporte prioritario"] },
];

export default function RegisterPage() {
  const [form, setForm] = useState({ email: "", password: "", username: "", plan: "starter" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    const res = await api.signup(form.email, form.password, form.username, form.plan);
    setLoading(false);
    if (res.error) return setError(res.error);
    setSuccess(res.data?.message || "Cuenta creada. Revisá tu email.");
    setTimeout(() => navigate("/"), 2000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4 py-8 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(220,38,38,0.08),transparent_50%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(220,38,38,0.05),transparent_50%)]" />
      <div className="w-full max-w-md relative">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-red-500 to-red-700 shadow-lg shadow-red-500/25 mb-4">
            <span className="text-3xl">🐺</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Unirse a la Jauría</h1>
          <p className="text-gray-500 mt-1 text-sm">Crea tu cuenta y empezá a cazar</p>
        </div>
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500 to-red-700 rounded-2xl blur opacity-20 group-hover:opacity-30 transition duration-300" />
          <form onSubmit={handleSubmit} className="relative bg-gray-900/80 backdrop-blur-xl rounded-2xl p-6 space-y-4 border border-gray-800/50">
            {error && (
              <div className="flex items-center gap-2 bg-red-900/40 text-red-300 px-4 py-2.5 rounded-xl text-sm border border-red-800/50">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div className="flex items-center gap-2 bg-green-900/40 text-green-300 px-4 py-2.5 rounded-xl text-sm border border-green-800/50">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>{success}</span>
              </div>
            )}
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Usuario</label>
              <input
                type="text" placeholder="lobo_alfa" value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Email</label>
              <input
                type="email" placeholder="tu@email.com" value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Contraseña</label>
              <input
                type="password" placeholder="••••••••" value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all"
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Plan</label>
              <div className="grid grid-cols-2 gap-2">
                {plans.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setForm({ ...form, plan: p.value })}
                    className={`relative p-3 rounded-xl border text-left transition-all ${
                      form.plan === p.value
                        ? "border-red-500/50 bg-red-500/10 shadow-lg shadow-red-500/10"
                        : "border-gray-700/50 bg-gray-800/30 hover:border-gray-600/50"
                    }`}
                  >
                    <p className={`text-sm font-semibold ${form.plan === p.value ? "text-white" : "text-gray-300"}`}>{p.label}</p>
                    <p className={`text-xs mt-0.5 ${form.plan === p.value ? "text-red-300" : "text-gray-500"}`}>{p.price}</p>
                    <p className={`text-xs mt-1 ${form.plan === p.value ? "text-gray-300" : "text-gray-600"}`}>{p.desc}</p>
                  </button>
                ))}
              </div>
            </div>
            <button
              type="submit" disabled={loading}
              className="w-full py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold hover:from-red-600 hover:to-red-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-red-500/20 hover:shadow-red-500/30"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                  Creando...
                </span>
              ) : "Crear Cuenta"}
            </button>
            <p className="text-center text-sm text-gray-500">
              ¿Ya tenés cuenta?{" "}
              <Link to="/" className="text-red-400 hover:text-red-300 font-medium transition-colors">Iniciar Sesión</Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
