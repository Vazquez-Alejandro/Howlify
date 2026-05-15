import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import Logo from "../components/Logo";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const res = await api.login(email, password);
    setLoading(false);
    if (res.error) return setError(res.error);
    if (res.data) {
      login(res.data.token, res.data.user);
      navigate("/dashboard");
    }
  };

  return (
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
          <form onSubmit={handleSubmit} className="relative bg-gray-900/80 backdrop-blur-xl rounded-2xl p-8 space-y-5 border border-gray-800/50">
            <h3 className="text-xl font-bold text-white">Iniciar Sesión</h3>
            {error && (
              <div className="flex items-center gap-2 bg-red-900/40 text-red-300 px-4 py-2.5 rounded-xl text-sm border border-red-800/50">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>{error}</span>
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
            <p className="text-center text-sm text-gray-500">
              ¿No tenés cuenta?{" "}
              <Link to="/register" className="text-red-400 hover:text-red-300 font-medium transition-colors">Registrate</Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
