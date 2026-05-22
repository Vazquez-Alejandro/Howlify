import { Link } from "react-router-dom";
import PageTransition from "../components/PageTransition";

export default function NotFoundPage() {
  return (
    <PageTransition>
      <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
        <div className="text-center max-w-md">
          <div className="text-7xl font-extrabold text-red-500/30 mb-4">404</div>
          <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-5">
            <span className="text-2xl">🐺</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Página no encontrada</h1>
          <p className="text-gray-500 text-sm mb-8">El Lobo no encontró lo que buscás. La página puede haber sido movida o no existir.</p>
          <Link to="/" className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold text-sm hover:from-red-600 hover:to-red-700 transition-all shadow-lg shadow-red-500/20">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0v-4a1 1 0 011-1h2a1 1 0 011 1v4" /></svg>
            Volver al inicio
          </Link>
        </div>
      </div>
    </PageTransition>
  );
}
