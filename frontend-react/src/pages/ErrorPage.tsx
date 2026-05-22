import { Link, useLocation } from "react-router-dom";
import PageTransition from "../components/PageTransition";

export default function ErrorPage() {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const mensaje = params.get("mensaje") || "Algo salió mal. El Lobo ya está investigando.";

  return (
    <PageTransition>
      <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
        <div className="text-center max-w-md">
          <div className="text-7xl font-extrabold text-red-500/30 mb-4">500</div>
          <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-5">
            <span className="text-2xl">🐺</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Error inesperado</h1>
          <p className="text-gray-500 text-sm mb-6">{mensaje}</p>
          <div className="flex gap-3 justify-center">
            <button onClick={() => window.location.reload()} className="px-5 py-3 bg-red-500/15 text-red-400 rounded-xl text-sm font-semibold hover:bg-red-500/25 transition-all border border-red-500/20">
              ↻ Reintentar
            </button>
            <Link to="/" className="px-5 py-3 bg-gray-800/50 text-gray-300 rounded-xl text-sm font-semibold hover:bg-gray-700/50 transition-all border border-gray-700/50">
              Volver al inicio
            </Link>
          </div>
          <p className="text-xs text-gray-600 mt-6">
            Si el problema persiste, contactanos a{" "}
            <a href="mailto:soporte@howlify.app" className="text-red-400 hover:text-red-300 underline underline-offset-2">soporte@howlify.app</a>
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
