import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import { traducirError } from "../utils/errors";
import PageTransition from "../components/PageTransition";
import Logo from "../components/Logo";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [sendingVerification, setSendingVerification] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const esErrorConfirmacion = formError.toLowerCase().includes("confirm");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    if (!email.trim()) { setFormError("Ingresá tu email"); return; }
    if (!password) { setFormError("Ingresá tu contraseña"); return; }
    setLoading(true);
    const res = await api.login(email, password);
    setLoading(false);
    if (res.error) {
      const msg = traducirError(res.error);
      setFormError(msg);
      return toast(msg, "error");
    }
    if (res.data) {
      login(res.data.token, res.data.user);
      navigate("/dashboard");
    }
  };

  const handleResendVerification = async () => {
    if (!email.trim()) { toast("Ingresá tu email primero", "error"); return; }
    setSendingVerification(true);
    const res = await api.resendVerification(email);
    setSendingVerification(false);
    if (res.error) { toast(traducirError(res.error), "error"); return; }
    toast("Correo de verificación reenviado", "success");
  };

  return (
    <PageTransition>
      <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(220,38,38,0.08),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(220,38,38,0.05),transparent_50%)]" />
        <div className="w-full max-w-xl relative">
          <div className="text-center mb-10">
            <Logo className="mb-5" size="xl" />
            <h1 className="text-4xl font-extrabold text-white tracking-tight">Howlify</h1>
            <p className="text-gray-500 mt-2 text-sm">Price Intelligence Platform</p>
          </div>
          <div className="relative group">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500 to-red-700 rounded-2xl blur opacity-20 group-hover:opacity-30 transition duration-300" />
            <form onSubmit={handleSubmit} className="relative bg-gray-900/80 backdrop-blur-xl rounded-2xl p-8 space-y-5" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
              <h3 className="text-xl font-bold text-white">Iniciar Sesión</h3>
              {formError && (
                <div className="px-4 py-3 bg-red-900/30 border border-red-500/30 rounded-xl text-sm text-red-300">
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <span>{formError}</span>
                  </div>
                  {esErrorConfirmacion && (
                    <button onClick={handleResendVerification} disabled={sendingVerification}
                      className="mt-2 text-xs text-red-400 hover:text-red-300 underline underline-offset-2 transition-colors disabled:opacity-50">
                      {sendingVerification ? "⏳ Reenviando..." : "📧 Reenviar correo de verificación"}
                    </button>
                  )}
                </div>
              )}
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Email</label>
                <input
                  type="email" placeholder="tu@email.com" value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-5 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all text-base"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider ml-1">Contraseña</label>
                <input
                  type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-5 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 transition-all text-base"
                  required
                />
              </div>
              <button
                type="submit" disabled={loading}
                className="w-full py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold text-base hover:from-red-600 hover:to-red-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-red-500/20 hover:shadow-red-500/30"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                    Entrando...
                  </span>
                ) : "Entrar"}
              </button>
              <div className="flex items-center justify-between text-sm">
                <Link to="/forgot-password" className="text-gray-500 hover:text-red-400 transition-colors">¿Olvidaste tu contraseña?</Link>
                <Link to="/register" className="text-red-400 hover:text-red-300 font-medium transition-colors">Registrate</Link>
              </div>
              <p className="text-center text-xs text-gray-600">
                Al iniciar sesión aceptás nuestros{" "}
                <Link to="/terms" className="text-gray-500 hover:text-red-400 transition-colors underline underline-offset-2">Términos</Link>
                {" y "}
                <Link to="/privacy" className="text-gray-500 hover:text-red-400 transition-colors underline underline-offset-2">Privacidad</Link>
              </p>
            </form>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
