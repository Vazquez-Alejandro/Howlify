import { Link } from "react-router-dom";
import PageTransition from "../components/PageTransition";
import Logo from "../components/Logo";

const PLANS = [
  {
    name: "Starter",
    price: "$9/mes",
    desc: "Para empezar a monitorear",
    features: ["5 cacerías activas", "C/1 hora o más", "Alertas email", "Tiendas ML + genéricas"],
    cta: "Probar gratis",
    href: "/register",
  },
  {
    name: "Pro",
    price: "$15/mes",
    desc: "Para cazadores seriales",
    features: ["15 cacerías activas", "C/15 min o más", "Alertas WhatsApp", "Exportación CSV"],
    cta: "Probar gratis",
    href: "/register",
    popular: true,
  },
  {
    name: "Business Reseller",
    price: "$39/mes",
    desc: "Para reventa y equipos",
    features: ["40 cacerías activas", "Dashboard empresa", "Multi-tienda por cacería", "Reporte diario"],
    cta: "Probar gratis",
    href: "/register",
  },
  {
    name: "Business Monitor",
    price: "$79/mes",
    desc: "Monitoreo profesional",
    features: ["100 cacerías activas", "Rankings de negocio", "Dashboard empresa completo", "Soporte prioritario"],
    cta: "Probar gratis",
    href: "/register",
  },
];

const FEATURES = [
  { icon: "🛒", title: "Multi-plataforma", desc: "Monitoreá Mercado Libre y más. Detección de violaciones MAP, precios dinámicos y cambios de stock." },
  { icon: "📡", title: "Alertas en Tiempo Real", desc: "Recibí notificaciones por Telegram, WhatsApp o email cuando un precio cambie o se detecte una infracción." },
  { icon: "📊", title: "Dashboard Inteligente", desc: "Visualizá rankings de riesgo, históricos de precio y métricas de cumplimiento en un solo lugar." },
  { icon: "📤", title: "Exportación a Google Sheets", desc: "Exportá toda la data de monitoreo a tu propia planilla para análisis y reportes personalizados." },
];

export default function LandingPage() {
  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(220,38,38,0.06),transparent_50%)] pointer-events-none" />

        <nav className="relative z-10 flex items-center justify-between w-full max-w-6xl px-6 py-4">
          <div className="flex items-center gap-3">
            <Logo size="md" />
            <span className="text-xl font-bold">Howlify</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white transition-colors">Iniciar Sesión</Link>
            <Link to="/register" className="px-5 py-2 text-sm font-semibold bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:from-red-600 hover:to-red-700 transition-all shadow-lg shadow-red-500/20">Registrarse</Link>
          </div>
        </nav>

        <section className="relative z-10 w-full max-w-5xl px-6 pt-20 pb-16 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-red-500/10 border border-red-500/20 rounded-full text-sm text-red-400 mb-8">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            Price Intelligence Platform
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-tight">
            Nunca más te pierdas{" "}
            <span className="bg-gradient-to-r from-red-400 to-red-600 bg-clip-text text-transparent">una oportunidad</span>
          </h1>
          <p className="mt-6 text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
            Howlify monitorea precios 24/7, detecta violaciones de MAP y te alerta al instante.
            Tomá decisiones informadas sin pasar horas mirando pantallas.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link to="/register" className="px-8 py-3.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold text-lg hover:from-red-600 hover:to-red-700 transition-all shadow-xl shadow-red-500/20 hover:shadow-red-500/30">
              Probar 7 días gratis
            </Link>
            <Link to="/login" className="px-8 py-3.5 bg-gray-800/60 border border-gray-700/50 text-gray-300 rounded-xl font-semibold text-lg hover:bg-gray-700/50 hover:text-white transition-all">
              Iniciar sesión
            </Link>
          </div>
        </section>

        <section className="relative z-10 w-full max-w-6xl px-6 py-16">
          <h2 className="text-3xl font-bold text-center mb-4">Todo lo que necesitás</h2>
          <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">Monitoreo inteligente, alertas instantáneas, todo en un dashboard diseñado para cazadores de ofertas.</p>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {FEATURES.map((f) => (
              <div key={f.title} className="bg-gray-900/60 rounded-2xl p-6 hover:bg-gray-900/80 transition-all" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
                <span className="text-3xl">{f.icon}</span>
                <h3 className="text-lg font-semibold mt-4 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="relative z-10 w-full max-w-6xl px-6 py-16">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full text-sm text-green-400 mb-4">
              🎁 7 días gratis · Sin tarjeta
            </div>
            <h2 className="text-3xl font-bold text-center mb-4">Planes simples</h2>
            <p className="text-gray-400 text-center max-w-xl mx-auto">Empezá gratis, escalá cuando lo necesites. Sin contratos ni sorpresas.</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {PLANS.map((p) => (
              <div
                key={p.name}
                className={`relative rounded-2xl p-6 flex flex-col border ${p.popular ? 'bg-gradient-to-b from-red-500/10 to-gray-900/80 border-red-500/30 scale-[1.02]' : 'bg-gray-900/60 border-gray-700/30'}`}
              >
                {p.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-red-500 to-red-600 rounded-full text-xs font-semibold shadow-lg z-10">Más popular</div>
                )}
                <h3 className={`text-xl font-bold ${p.popular ? 'pt-2' : ''}`}>{p.name}</h3>
                <p className="text-3xl font-extrabold mt-3">{p.price}</p>
                <p className="text-sm text-gray-400 mt-1">{p.desc}</p>
                <ul className="mt-6 space-y-3 flex-1">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-gray-300">
                      <span className="text-green-400">✓</span> {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to={p.href}
                  className={`mt-8 block text-center py-3 rounded-xl font-semibold text-sm transition-all ${
                    p.popular
                      ? 'bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 shadow-lg shadow-red-500/20'
                      : 'bg-gray-800/60 text-gray-300 hover:bg-gray-700/50 hover:text-white border border-gray-700/30'
                  }`}
                >
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>
        </section>

        <footer className="relative z-10 w-full border-t border-gray-800/50 mt-16">
          <div className="max-w-6xl mx-auto px-6 py-8 flex items-center justify-between text-sm text-gray-500">
            <span>© 2026 Howlify. Todos los derechos reservados.</span>
            <div className="flex items-center gap-4">
              <span>Términos</span>
              <span>Privacidad</span>
              <a href="mailto:howlify.app@gmail.com" className="hover:text-gray-300 transition-colors">Contacto</a>
            </div>
          </div>
        </footer>
      </div>
    </PageTransition>
  );
}
