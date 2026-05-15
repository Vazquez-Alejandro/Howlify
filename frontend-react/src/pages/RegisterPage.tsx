import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api/client";

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
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-5xl">🐺</h1>
          <h2 className="text-2xl font-bold text-white mt-2">Unirse a la Jauría</h2>
        </div>
        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-6 space-y-4 border border-gray-800">
          {error && <div className="bg-red-900/50 text-red-300 px-4 py-2 rounded-lg text-sm">{error}</div>}
          {success && <div className="bg-green-900/50 text-green-300 px-4 py-2 rounded-lg text-sm">{success}</div>}
          <input
            type="text" placeholder="Usuario" value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
            required
          />
          <input
            type="email" placeholder="Email" value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
            required
          />
          <input
            type="password" placeholder="Contraseña" value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
            required
          />
          <select
            value={form.plan}
            onChange={(e) => setForm({ ...form, plan: e.target.value })}
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-red-500"
          >
            <option value="starter">Starter</option>
            <option value="pro">Pro</option>
          </select>
          <button
            type="submit" disabled={loading}
            className="w-full py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-medium hover:from-red-600 hover:to-red-700 transition disabled:opacity-50"
          >
            {loading ? "Creando..." : "Crear Cuenta"}
          </button>
          <p className="text-center text-sm text-gray-400">
            ¿Ya tenés cuenta? <Link to="/" className="text-red-400 hover:text-red-300">Iniciar Sesión</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
