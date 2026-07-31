import { Link } from "react-router-dom";
import { useState, useEffect } from "react";
import PageTransition from "../components/PageTransition";
import Logo from "../components/Logo";

const PLANS = [
  {
    name: "Starter",
    price: 9,
    desc: "Para empezar a monitorear",
    features: [
      { text: "5 cacerías activas", included: true },
      { text: "Frecuencia cada 1 hora", included: true },
      { text: "Alertas por email", included: true },
      { text: "MercadoLibre + tiendas genéricas", included: true },
      { text: "Historial de precios", included: true },
      { text: "Exportación CSV", included: false },
      { text: "Alertas WhatsApp", included: false },
      { text: "API MercadoLibre", included: false },
    ],
    cta: "Empezar gratis",
    href: "/register",
  },
  {
    name: "Pro",
    price: 15,
    desc: "Para cazadores seriales",
    features: [
      { text: "15 cacerías activas", included: true },
      { text: "Frecuencia cada 15 minutos", included: true },
      { text: "Alertas por email", included: true },
      { text: "MercadoLibre + tiendas genéricas", included: true },
      { text: "Historial de precios", included: true },
      { text: "Exportación CSV", included: true },
      { text: "Alertas WhatsApp", included: true },
      { text: "API MercadoLibre oficial", included: true },
    ],
    cta: "Empezar gratis",
    href: "/register",
    popular: true,
  },
];

const FEATURES = [
  {
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
      </svg>
    ),
    title: "Cacerías automáticas",
    desc: "Creá reglas de monitoreo y Howlify revisa los precios por vos. Cada 15 minutos o cada hora según tu plan.",
  },
  {
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
      </svg>
    ),
    title: "Alertas instantáneas",
    desc: "Recibí notificaciones por email, Telegram o WhatsApp cuando el precio baje o aparezca una oferta.",
  },
  {
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
      </svg>
    ),
    title: "Gráficos e historial",
    desc: "Visualizá la evolución de precios con gráficos intuitivos. Detectá tendencias y comprá en el momento justo.",
  },
  {
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
      </svg>
    ),
    title: "Detección de precio personalizado",
    desc: "ML muestra precios distintos según quién mira. Howlify lo detecta y te alerta si el precio no es el real.",
  },
  {
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
      </svg>
    ),
    title: "Multi-plataforma",
    desc: "Monitoreá precios en MercadoLibre, tiendas online, vuelos y alojamientos. Todo desde un solo lugar.",
  },
  {
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
      </svg>
    ),
    title: "Exportación de datos",
    desc: "Exportá precios, historial y alertas a CSV para análisis en Excel o Google Sheets.",
  },
];

const STEPS = [
  { num: "1", title: "Creá tu cacería", desc: "Pegá el link de un producto en MercadoLibre o cualquier tienda online." },
  { num: "2", title: "Configurá alertas", desc: "Definí el precio objetivo y elegí cómo querés recibir notificaciones." },
  { num: "3", title: "Howlify monitorea", desc: "El sistema revisa el precio automáticamente cada 15 minutos o cada hora." },
  { num: "4", title: "Recibí la alerta", desc: "Cuando el precio baj o hay oferta, te avisamos al instante." },
];

function CountUp({ target }: { target: number }) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let start = 0;
    const duration = 2000;
    const increment = target / (duration / 16);
    const timer = setInterval(() => {
      start += increment;
      if (start >= target) { setCount(target); clearInterval(timer); }
      else setCount(Math.floor(start));
    }, 16);
    return () => clearInterval(timer);
  }, [target]);
  return <span>{count.toLocaleString("es-AR")}</span>;
}

export default function LandingPage() {
  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-950 text-white">
        {/* ─── Hero ─── */}
        <div className="relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(239,68,68,0.08),transparent_60%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,rgba(239,68,68,0.04),transparent_50%)]" />

          <nav className="relative z-10 flex items-center justify-between w-full max-w-6xl mx-auto px-6 py-5">
            <div className="flex items-center gap-3">
              <Logo size="md" />
              <span className="text-xl font-bold tracking-tight">Howlify</span>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/login" className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-white transition-colors">Iniciar Sesión</Link>
              <Link to="/register" className="px-5 py-2.5 text-sm font-semibold bg-white text-gray-950 rounded-xl hover:bg-gray-100 transition-all">
                Empezar gratis
              </Link>
            </div>
          </nav>

          <div className="relative z-10 w-full max-w-5xl mx-auto px-6 pt-24 pb-28 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-red-500/10 border border-red-500/20 rounded-full text-sm text-red-400 mb-8">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              Monitoreo de precios en tiempo real
            </div>
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1]">
              Nunca más te pierdas{" "}
              <span className="bg-gradient-to-r from-red-400 to-red-600 bg-clip-text text-transparent">
                una oferta
              </span>
            </h1>
            <p className="mt-7 text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed">
              Howlify monitorea precios 24/7 en MercadoLibre y tiendas online.
              Recibí alertas al instante cuando haya ofertas o el precio que buscás.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/register"
                className="w-full sm:w-auto px-8 py-4 bg-white text-gray-950 rounded-xl font-semibold text-base hover:bg-gray-100 transition-all shadow-xl shadow-white/5"
              >
                Empezar gratis — 7 días
              </Link>
              <Link
                to="/login"
                className="w-full sm:w-auto px-8 py-4 bg-gray-800/60 border border-gray-700/50 text-gray-300 rounded-xl font-semibold text-base hover:bg-gray-700/50 hover:text-white transition-all"
              >
                Ya tengo cuenta
              </Link>
            </div>

            {/* Social proof */}
            <div className="mt-16 flex items-center justify-center gap-8 sm:gap-12 text-sm text-gray-500">
              <div className="text-center">
                <p className="text-2xl font-bold text-white"><CountUp target={1200} />+</p>
                <p className="mt-1">Cacerías activas</p>
              </div>
              <div className="w-px h-10 bg-gray-800" />
              <div className="text-center">
                <p className="text-2xl font-bold text-white"><CountUp target={50} />K+</p>
                <p className="mt-1">Alertas enviadas</p>
              </div>
              <div className="w-px h-10 bg-gray-800" />
              <div className="text-center">
                <p className="text-2xl font-bold text-white">24/7</p>
                <p className="mt-1">Monitoreo activo</p>
              </div>
            </div>
          </div>
        </div>

        {/* ─── Cómo funciona ─── */}
        <section className="relative z-10 w-full max-w-5xl mx-auto px-6 py-20">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-red-400 tracking-wider uppercase mb-3">Simple y automático</p>
            <h2 className="text-3xl sm:text-4xl font-bold">Cómo funciona</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {STEPS.map((s) => (
              <div key={s.num} className="relative text-center p-6">
                <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5">
                  <span className="text-red-400 font-bold text-lg">{s.num}</span>
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{s.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ─── Features ─── */}
        <section className="relative z-10 w-full max-w-6xl mx-auto px-6 py-20">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-red-400 tracking-wider uppercase mb-3">Funcionalidades</p>
            <h2 className="text-3xl sm:text-4xl font-bold">Todo lo que necesitás</h2>
            <p className="mt-4 text-gray-400 max-w-xl mx-auto">Monitoreo inteligente, alertas instantáneas, historial de precios. Diseñado para encontrar las mejores ofertas.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f) => (
              <div key={f.title} className="group p-6 rounded-2xl bg-gray-900/40 border border-gray-800/60 hover:border-gray-700/60 hover:bg-gray-900/60 transition-all duration-300">
                <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 mb-5 group-hover:bg-red-500/15 transition-colors">
                  {f.icon}
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ─── Pricing ─── */}
        <section className="relative z-10 w-full max-w-5xl mx-auto px-6 py-20">
          <div className="text-center mb-14">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full text-sm text-green-400 mb-5">
              7 días gratis · Sin tarjeta de crédito
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Planes para todos</h2>
            <p className="text-gray-400 max-w-lg mx-auto">Empezá gratis, escalá cuando lo necesites. Sin contratos ni sorpresas.</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {PLANS.map((p) => (
              <div
                key={p.name}
                className={`relative rounded-2xl p-8 flex flex-col border transition-all duration-300 ${
                  p.popular
                    ? "bg-gradient-to-b from-red-500/8 to-gray-900/80 border-red-500/30 shadow-xl shadow-red-500/5"
                    : "bg-gray-900/40 border-gray-800/60 hover:border-gray-700/60"
                }`}
              >
                {p.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-red-500 to-red-600 rounded-full text-xs font-semibold shadow-lg shadow-red-500/25 whitespace-nowrap">
                    Más popular
                  </div>
                )}
                <div className="mb-6">
                  <h3 className="text-xl font-bold">{p.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{p.desc}</p>
                </div>
                <div className="mb-8">
                  <span className="text-5xl font-extrabold">${p.price}</span>
                  <span className="text-gray-500 text-sm ml-1">/mes</span>
                </div>
                <ul className="space-y-3 mb-8 flex-1">
                  {p.features.map((f) => (
                    <li key={f.text} className="flex items-center gap-3 text-sm">
                      {f.included ? (
                        <svg className="w-5 h-5 text-green-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5 text-gray-700 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      )}
                      <span className={f.included ? "text-gray-300" : "text-gray-600"}>{f.text}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  to={p.href}
                  className={`block text-center py-3.5 rounded-xl font-semibold text-sm transition-all ${
                    p.popular
                      ? "bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 shadow-lg shadow-red-500/20 hover:shadow-red-500/30"
                      : "bg-gray-800/60 text-gray-300 hover:bg-gray-700/50 hover:text-white border border-gray-700/30"
                  }`}
                >
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>
        </section>

        {/* ─── FAQ ─── */}
        <section className="relative z-10 w-full max-w-3xl mx-auto px-6 py-20">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-red-400 tracking-wider uppercase mb-3">Preguntas frecuentes</p>
            <h2 className="text-3xl sm:text-4xl font-bold">¿Tenés dudas?</h2>
          </div>
          <div className="space-y-4">
            {[
              { q: "¿Qué es una cacería?", a: "Una regla de monitoreo que revisa automáticamente el precio de un producto en una URL que vos definas. Podés configurar el precio objetivo y la frecuencia de revisión." },
              { q: "¿Cómo recibo las alertas?", a: "Según tu plan, podés recibir alertas por email, Telegram o WhatsApp. Configurás tu canal preferido y te avisamos al instante cuando el precio cambie." },
              { q: "¿Puedo cancelar en cualquier momento?", a: "Sí, no hay contratos ni permanencia mínima. Cancelás cuando quierás desde tu perfil y dejás de ser cobrado." },
              { q: "¿Qué tiendas soporta?", a: "MercadoLibre (con API oficial), Despegar, Airbnb y cualquier tienda online genérica con Playwright." },
            ].map((item) => (
              <details key={item.q} className="group rounded-2xl bg-gray-900/40 border border-gray-800/60 overflow-hidden">
                <summary className="px-6 py-5 cursor-pointer text-sm font-medium text-white hover:text-red-400 transition-colors flex items-center justify-between">
                  {item.q}
                  <svg className="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </summary>
                <div className="px-6 pb-5 text-sm text-gray-400 leading-relaxed">{item.a}</div>
              </details>
            ))}
          </div>
        </section>

        {/* ─── CTA final ─── */}
        <section className="relative z-10 w-full max-w-4xl mx-auto px-6 py-20">
          <div className="relative rounded-3xl bg-gradient-to-b from-red-500/10 to-gray-900/80 border border-red-500/20 p-12 text-center overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(239,68,68,0.08),transparent_70%)]" />
            <div className="relative z-10">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">Empezá a ahorrar hoy</h2>
              <p className="text-gray-400 max-w-md mx-auto mb-8">Unite a miles de cazadores de ofertas que ya usan Howlify para no perderse ninguna oportunidad.</p>
              <Link
                to="/register"
                className="inline-block px-10 py-4 bg-white text-gray-950 rounded-xl font-semibold text-base hover:bg-gray-100 transition-all shadow-xl shadow-white/5"
              >
                Crear cuenta gratis
              </Link>
            </div>
          </div>
        </section>

        {/* ─── Footer ─── */}
        <footer className="relative z-10 w-full border-t border-gray-800/50">
          <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-500">
            <span>© 2026 Howlify. Todos los derechos reservados.</span>
            <div className="flex items-center gap-5">
              <Link to="/terms" className="hover:text-gray-300 transition-colors">Términos</Link>
              <Link to="/privacy" className="hover:text-gray-300 transition-colors">Privacidad</Link>
              <a href="mailto:howlify.app@gmail.com" className="hover:text-gray-300 transition-colors">Contacto</a>
            </div>
          </div>
        </footer>
      </div>
    </PageTransition>
  );
}
