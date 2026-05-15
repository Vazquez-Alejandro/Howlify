import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";
import { useToast } from "../components/Toast";
import PageTransition from "../components/PageTransition";
import Logo from "../components/Logo";

type Category = "personal" | "business";

interface Plan {
  value: string;
  label: string;
  price: string;
  features: string[];
  popular?: boolean;
}

const plans: Record<Category, Plan[]> = {
  personal: [
    { value: "starter", label: "Starter", price: "USD 9/mes", features: ["5 cacerías activas", "C/1 hora o más", "Alertas email", "Tiendas ML + genéricas"] },
    { value: "pro", label: "Pro", price: "USD 15/mes", features: ["15 cacerías activas", "C/15 min o más", "Alertas WhatsApp", "Export CSV"], popular: true },
  ],
  business: [
    { value: "business_reseller", label: "Business Reseller", price: "USD 39/mes", features: ["40 cacerías activas", "Dashboard empresa", "Multi-tienda por cacería", "Reporte diario"], popular: true },
    { value: "business_monitor", label: "Business Monitor", price: "USD 79/mes", features: ["100 cacerías activas", "Rankings de negocio", "Dashboard empresa completo", "Soporte prioritario"] },
  ],
};

export default function RegisterPage() {
  const [category, setCategory] = useState<Category>("personal");
  const [form, setForm] = useState({ email: "", password: "", username: "", plan: "starter" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    const res = await api.signup(form.email, form.password, form.username, form.plan);
    setLoading(false);
    if (res.error) return toast(res.error, "error");
    setSuccess(res.data?.message || "Cuenta creada. Revisá tu email.");
    toast(res.data?.message || "Cuenta creada. Revisá tu email.", "success");
    setTimeout(() => navigate("/"), 2000);
  };

  return (
    <PageTransition>
      <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4 py-8 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(220,38,38,0.08),transparent_50%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(220,38,38,0.05),transparent_50%)]" />
      <div className="w-full max-w-2xl relative">
        <div className="text-center mb-10">
          <Logo className="mb-5" size="xl" />
          <h1 className="text-4xl font-extrabold text-white tracking-tight">Unirse a la Jauría</h1>
          <p className="text-gray-500 mt-2 text-sm">Elegí tu plan y empezá a cazar</p>
        </div>
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500 to-red-700 rounded-2xl blur opacity-20 group-hover:opacity-30 transition duration-300" />
          <form onSubmit={handleSubmit} className="relative bg-gray-900/80 backdrop-blur-xl rounded-2xl p-8 space-y-6 border border-gray-800/50">
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
                className="w-full px-5 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all text-base"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Email</label>
              <input
                type="email" placeholder="tu@email.com" value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full px-5 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all text-base"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Contraseña</label>
              <input
                type="password" placeholder="••••••••" value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full px-5 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all text-base"
                required
              />
            </div>

            <div className="space-y-3">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Plan</label>
              <div className="flex gap-2 p-1 bg-gray-800/30 rounded-xl border border-gray-700/50">
                {(["personal", "business"] as Category[]).map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => { setCategory(cat); setForm({ ...form, plan: plans[cat][0].value }); }}
                    className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                      category === cat
                        ? "bg-red-500/20 text-red-300 shadow-sm"
                        : "text-gray-500 hover:text-gray-300"
                    }`}
                  >
                    {cat === "personal" ? "Uso Personal" : "Business"}
                  </button>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-4">
                {plans[category].map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setForm({ ...form, plan: p.value })}
                    className={`relative p-5 rounded-xl border text-left transition-all ${
                      form.plan === p.value
                        ? "border-red-500/50 bg-red-500/10 shadow-lg shadow-red-500/10"
                        : "border-gray-700/50 bg-gray-800/30 hover:border-gray-600/50"
                    }`}
                  >
                    {p.popular && form.plan !== p.value && (
                      <span className="absolute -top-2.5 -right-2.5 px-2.5 py-0.5 bg-gradient-to-r from-red-500 to-red-600 text-white text-[10px] font-bold rounded-md shadow-lg shadow-red-500/30">
                        POPULAR
                      </span>
                    )}
                    {form.plan === p.value && (
                      <span className="absolute -top-2.5 -right-2.5 px-2.5 py-0.5 bg-gradient-to-r from-red-500 to-red-600 text-white text-[10px] font-bold rounded-md shadow-lg shadow-red-500/30">
                        SELECCIONADO
                      </span>
                    )}
                    <p className={`text-base font-bold ${form.plan === p.value ? "text-white" : "text-gray-200"}`}>{p.label}</p>
                    <p className={`text-xl font-extrabold mt-1.5 ${form.plan === p.value ? "text-red-400" : "text-gray-400"}`}>{p.price}</p>
                    <ul className="mt-3 space-y-1.5">
                      {p.features.map((f, i) => (
                        <li key={i} className={`flex items-center gap-1.5 text-sm ${form.plan === p.value ? "text-gray-300" : "text-gray-500"}`}>
                          <svg className={`w-3.5 h-3.5 shrink-0 ${form.plan === p.value ? "text-red-400" : "text-gray-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                          {f}
                        </li>
                      ))}
                    </ul>
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit" disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold text-base hover:from-red-600 hover:to-red-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-red-500/20 hover:shadow-red-500/30"
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
    </PageTransition>
  );
}
