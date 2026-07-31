import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useToast } from "../components/Toast";
import { traducirError } from "../utils/errors";
import PageTransition from "../components/PageTransition";
import Logo from "../components/Logo";

interface Plan {
  value: string;
  label: string;
  price: string;
  features: string[];
  popular?: boolean;
}

const plans: Plan[] = [
  { value: "starter", label: "Starter", price: "USD 9/mes", features: ["5 cacerías activas", "C/1 hora o más", "Alertas email", "Tiendas ML + genéricas"] },
  { value: "pro", label: "Pro", price: "USD 15/mes", features: ["15 cacerías activas", "C/15 min o más", "Alertas WhatsApp", "Export CSV"], popular: true },
];

export default function RegisterPage() {
  const [form, setForm] = useState({ email: "", password: "", confirmPassword: "", username: "", plan: "starter" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState("");
  const [sendingVerification, setSendingVerification] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 6) return setError("La contraseña debe tener al menos 6 caracteres");
    if (form.password !== form.confirmPassword) return setError("Las contraseñas no coinciden");
    setSuccess("");
    setLoading(true);
    const res = await api.signup(form.email, form.password, form.username, form.plan);
    setLoading(false);
    if (res.error) { setError(traducirError(res.error)); return toast(traducirError(res.error), "error"); }
    setRegisteredEmail(form.email);
    setSuccess(res.data?.message || "Cuenta creada. Revisá tu email.");
    toast(res.data?.message || "Cuenta creada. Revisá tu email.", "success");
  };

  const handleResendVerification = async () => {
    if (!registeredEmail) return;
    setSendingVerification(true);
    const res = await api.resendVerification(registeredEmail);
    setSendingVerification(false);
    if (res.error) { toast(traducirError(res.error), "error"); return; }
    toast("Correo de verificación reenviado", "success");
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
          <form onSubmit={handleSubmit} className="relative bg-gray-900/80 backdrop-blur-xl rounded-2xl p-8 space-y-6" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
            {error && (
              <div className="flex items-center gap-2 bg-red-900/40 text-red-300 px-4 py-2.5 rounded-xl text-sm border border-red-800/50">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div className="bg-green-900/30 rounded-2xl p-6 text-center border border-green-800/40">
                <div className="text-4xl mb-3">📧</div>
                <h3 className="text-lg font-bold text-white mb-2">Verificá tu email</h3>
                <p className="text-sm text-gray-400 mb-1">Te enviamos un correo a:</p>
                <p className="text-base font-medium text-green-400 mb-4">{registeredEmail}</p>
                <p className="text-xs text-gray-500 mb-5">Hacé clic en el enlace que te llegó para activar tu cuenta. Si no lo ves, revisá la carpeta de spam.</p>
                <button onClick={handleResendVerification} disabled={sendingVerification}
                  className="px-5 py-2 bg-gray-800/50 text-gray-300 rounded-xl text-sm hover:bg-gray-700/50 transition-all border border-gray-700/50 disabled:opacity-50 disabled:cursor-not-allowed">
                  {sendingVerification ? "⏳" : "Reenviar correo"}
                </button>
                <div className="mt-4">
                  <Link to="/login" className="text-sm text-red-400 hover:text-red-300 transition-colors font-medium">
                    Ya lo verifiqué — Iniciar sesión →
                  </Link>
                </div>
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
                required minLength={6}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Repetir contraseña</label>
              <input
                type="password" placeholder="••••••••" value={form.confirmPassword}
                onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                className={`w-full px-5 py-3 bg-gray-800/50 border rounded-xl text-white placeholder-gray-600 focus:outline-none focus:ring-1 transition-all text-base ${
                  form.confirmPassword && form.password !== form.confirmPassword
                    ? "border-red-500/50 focus:border-red-500 focus:ring-red-500/20"
                    : "border-gray-700/50 focus:border-red-500/50 focus:ring-red-500/20"
                }`}
                required
              />
              {form.confirmPassword && form.password !== form.confirmPassword && (
                <p className="text-xs text-red-400 ml-1 mt-1">Las contraseñas no coinciden</p>
              )}
            </div>

            <div className="space-y-3">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Plan</label>
              <div className="grid grid-cols-2 gap-4">
                {plans.map((p) => (
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
            <div className="text-center text-sm">
              <p className="text-gray-500">
                ¿Ya tenés cuenta?{" "}
                <Link to="/login" className="text-red-400 hover:text-red-300 font-medium transition-colors">Iniciar Sesión</Link>
              </p>
              <p className="text-gray-600 mt-4 text-xs">
                Al registrarte aceptás nuestros{" "}
                <Link to="/terms" className="text-gray-500 hover:text-red-400 transition-colors underline underline-offset-2">Términos</Link>
                {" y "}
                <Link to="/privacy" className="text-gray-500 hover:text-red-400 transition-colors underline underline-offset-2">Política de Privacidad</Link>
                {" · "}
                <Link to="/aviso-legal" className="text-gray-500 hover:text-red-400 transition-colors underline underline-offset-2">Aviso legal</Link>
              </p>
            </div>
          </form>
        </div>
      </div>
    </div>
    </PageTransition>
  );
}
