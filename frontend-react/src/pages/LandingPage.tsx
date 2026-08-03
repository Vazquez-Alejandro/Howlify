import { Link } from "react-router-dom";
import { useState, useEffect } from "react";
import PageTransition from "../components/PageTransition";
import Logo from "../components/Logo";

const PLANS = [
  {
    name: "Omega",
    price: 5,
    desc: "Para empezar a olfatear",
    features: [
      { text: "3 cacerías activas", included: true },
      { text: "Frecuencia cada 1 hora", included: true },
      { text: "Alertas por email + Telegram", included: true },
      { text: "MercadoLibre + tiendas genéricas", included: true },
      { text: "Historial de precios 7 días", included: true },
      { text: "Exportación CSV", included: false },
      { text: "Alertas WhatsApp", included: false },
      { text: "API MercadoLibre", included: false },
    ],
    cta: "Empezar gratis",
    href: "/register",
  },
  {
    name: "Beta",
    price: 15,
    desc: "Para cazadores seriales",
    features: [
      { text: "15 cacerías activas", included: true },
      { text: "Frecuencia cada 15 minutos", included: true },
      { text: "Alertas por email + WhatsApp", included: true },
      { text: "MercadoLibre + tiendas genéricas", included: true },
      { text: "Historial de precios ilimitado", included: true },
      { text: "Exportación CSV", included: true },
      { text: "Reportes periódicos", included: true },
      { text: "API MercadoLibre oficial", included: true },
    ],
    cta: "Empezar gratis",
    href: "/register",
    popular: true,
  },
  {
    name: "Alpha",
    price: 29,
    desc: "Líder del pack",
    features: [
      { text: "Cacerías ilimitadas", included: true },
      { text: "Frecuencia cada 5 minutos", included: true },
      { text: "Alertas por email + WhatsApp + Telegram", included: true },
      { text: "Todas las plataformas + vuelos + alojamientos", included: true },
      { text: "Historial de precios ilimitado", included: true },
      { text: "Exportación CSV + Sheets", included: true },
      { text: "Reportes prioritarios", included: true },
      { text: "Soporte prioritario", included: true },
    ],
    cta: "Empezar gratis",
    href: "/register",
  },
];

const FEATURES = [
  { icon: "bag", title: "Cacerías automáticas", desc: "Creá reglas de monitoreo y Howlify revisa los precios por vos. Cada 15 minutos o cada hora según tu plan." },
  { icon: "bell", title: "Alertas instantáneas", desc: "Recibí notificaciones por email, Telegram o WhatsApp cuando el precio baje o aparezca una oferta." },
  { icon: "chart", title: "Gráficos e historial", desc: "Visualizá la evolución de precios con gráficos intuitivos. Detectá tendencias y comprá en el momento justo." },
  { icon: "sparkle", title: "Detección de precio personalizado", desc: "ML muestra precios distintos según quién mira. Howlify lo detecta y te alerta si el precio no es el real." },
  { icon: "globe", title: "Multi-plataforma", desc: "Monitoreá precios en MercadoLibre, tiendas online, vuelos y alojamientos. Todo desde un solo lugar." },
  { icon: "download", title: "Exportación de datos", desc: "Exportá precios, historial y alertas a CSV para análisis en Excel o Google Sheets." },
];

const ICONS: Record<string, React.ReactNode> = {
  bag: <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" /></svg>,
  bell: <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" /></svg>,
  chart: <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>,
  sparkle: <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>,
  globe: <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" /></svg>,
  download: <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>,
};

const STEPS = [
  { num: "1", title: "Creá tu cacería", desc: "Pegá el link de un producto en MercadoLibre o cualquier tienda online." },
  { num: "2", title: "Definí el precio", desc: "Seteá el precio objetivo y la frecuencia de revisión que necesitás." },
  { num: "3", title: "Elegí las alertas", desc: "Configurá si querés recibir avisos por email, Telegram o WhatsApp." },
  { num: "4", title: "Howlify monitorea", desc: "El sistema revisa el precio automáticamente las 24 horas del día." },
  { num: "5", title: "Detectá ofertas", desc: "Howlify identifica descuentos reales y te distingue precios personalizados." },
  { num: "6", title: "Comprá informado", desc: "Recibí la alerta al instante y comprá en el momento justo." },
];

const FAQ = [
  { q: "¿Qué es una cacería?", a: "Una regla de monitoreo que revisa automáticamente el precio de un producto en una URL que vos definas. Podés configurar el precio objetivo y la frecuencia de revisión." },
  { q: "¿Cómo recibo las alertas?", a: "Según tu plan, podés recibir alertas por email, Telegram o WhatsApp. Configurás tu canal preferido y te avisamos al instante cuando el precio cambie." },
  { q: "¿Puedo cancelar en cualquier momento?", a: "Sí, no hay contratos ni permanencia mínima. Cancelás cuando quierás desde tu perfil y dejás de ser cobrado." },
  { q: "¿Qué tiendas soporta?", a: "MercadoLibre (con API oficial), Despegar, Airbnb y cualquier tienda online genérica con Playwright." },
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
  const [mobileMenu, setMobileMenu] = useState(false);
  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-950 text-gray-100">

        {/* NAV */}
        <nav className="relative z-10 flex items-center justify-between max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center gap-3">
            <Logo size="md" />
            <span className="text-xl font-bold">Howlify</span>
          </div>
          <div className="hidden md:flex items-center gap-3">
            <Link to="/login" className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-white transition-colors">Iniciar Sesión</Link>
            <Link to="/register" className="px-5 py-2.5 text-sm font-semibold bg-white text-gray-950 rounded-xl hover:bg-gray-100 transition-colors">Empezar gratis</Link>
          </div>
          <button onClick={() => setMobileMenu(!mobileMenu)} className="md:hidden p-2 text-gray-100" aria-label="Menú">
            {mobileMenu ? (
              <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            ) : (
              <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" /></svg>
            )}
          </button>
        </nav>
        {mobileMenu && (
          <div className="md:hidden relative z-10 flex flex-col items-center gap-3 px-6 pb-5 max-w-7xl mx-auto">
            <Link to="/login" onClick={() => setMobileMenu(false)} className="w-full text-center py-3 text-sm font-medium text-gray-400 rounded-xl border border-gray-700/30">Iniciar Sesión</Link>
            <Link to="/register" onClick={() => setMobileMenu(false)} className="w-full text-center py-3 text-sm font-semibold bg-white text-gray-950 rounded-xl">Empezar gratis</Link>
          </div>
        )}

        {/* HERO */}
        <section className="relative z-10 max-w-3xl mx-auto px-6 pt-12 pb-16 sm:pt-20 sm:pb-24 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-red-500/10 border border-red-500/20 rounded-full text-sm text-red-400 mb-8">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            Monitoreo de precios en tiempo real
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-extrabold leading-tight tracking-tight">
            Nunca más te pierdas{" "}
            <span className="bg-gradient-to-r from-red-400 to-red-600 bg-clip-text text-transparent">una oferta</span>
          </h1>
          <p className="mt-7 text-lg sm:text-xl text-gray-400 max-w-xl mx-auto leading-relaxed">
            Howlify monitorea precios 24/7 en MercadoLibre y tiendas online.
            Recibí alertas al instante cuando haya ofertas o el precio que buscás.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link to="/register" className="px-8 py-4 bg-white text-gray-950 rounded-xl font-semibold text-base hover:bg-gray-100 transition-colors">
              Empezar gratis — 7 días
            </Link>
            <Link to="/login" className="px-8 py-4 bg-gray-800/60 border border-gray-700/50 text-gray-300 rounded-xl font-semibold text-base hover:bg-gray-800 transition-colors">
              Ya tengo cuenta
            </Link>
          </div>
          <div className="mt-16 flex flex-wrap justify-center gap-6 sm:gap-12 text-sm text-gray-500">
            <div className="text-center">
              <p className="text-2xl font-bold text-white"><CountUp target={1200} />+</p>
              <p className="mt-1">Cacerías activas</p>
            </div>
            <div className="hidden sm:block w-px bg-gray-800" />
            <div className="text-center">
              <p className="text-2xl font-bold text-white"><CountUp target={50} />K+</p>
              <p className="mt-1">Alertas enviadas</p>
            </div>
            <div className="hidden sm:block w-px bg-gray-800" />
            <div className="text-center">
              <p className="text-2xl font-bold text-white">24/7</p>
              <p className="mt-1">Monitoreo activo</p>
            </div>
          </div>
        </section>

        {/* CÓMO FUNCIONA */}
        <section className="py-20">
          <div className="landing-section-md text-center">
            <p className="text-sm font-semibold text-red-400 uppercase tracking-widest mb-3">Simple y automático</p>
            <h2 className="text-3xl font-bold mb-14">Cómo funciona</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
              {STEPS.map((s) => (
                <div key={s.num} className="text-center">
                  <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5">
                    <span className="text-red-400 font-bold text-lg">{s.num}</span>
                  </div>
                  <h3 className="text-base font-semibold mb-2">{s.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section className="py-20 border-t border-gray-800/50">
          <div className="landing-section">
            <div className="text-center mb-14">
              <p className="text-sm font-semibold text-red-400 uppercase tracking-widest mb-3">Funcionalidades</p>
              <h2 className="text-3xl font-bold mb-4">Todo lo que necesitás</h2>
              <p className="text-gray-400 max-w-lg mx-auto">Monitoreo inteligente, alertas instantáneas, historial de precios.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {FEATURES.map((f) => (
                <div key={f.title} className="p-6 rounded-xl bg-gray-900/40 border border-gray-800/60">
                  <div className="w-11 h-11 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 mb-5">
                    {ICONS[f.icon]}
                  </div>
                  <h3 className="text-base font-semibold mb-2">{f.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* PRICING */}
        <section className="py-20 border-t border-gray-800/50">
          <div className="landing-section-md">
            <div className="text-center mb-14">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full text-sm text-green-400 mb-5">
                7 días gratis · Sin tarjeta de crédito
              </div>
              <h2 className="text-3xl font-bold mb-4">Elegí tu rango en la manada</h2>
              <p className="text-gray-400">Empezá gratis, escalá cuando lo necesites.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {PLANS.map((p) => (
                <div key={p.name} className={`relative rounded-xl p-8 flex flex-col ${p.popular ? "border border-red-500/30 bg-gradient-to-b from-red-500/8 to-gray-900/80" : "border border-gray-800/60 bg-gray-900/40"}`}>
                  {p.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-red-500 to-red-600 rounded-full text-xs font-semibold text-white whitespace-nowrap">
                      Más popular
                    </div>
                  )}
                  <h3 className="text-xl font-bold">{p.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{p.desc}</p>
                  <div className="mt-6 mb-8">
                    <span className="text-5xl font-extrabold">${p.price}</span>
                    <span className="text-gray-500 text-sm ml-1">/mes</span>
                  </div>
                  <ul className="list-none p-0 m-0 mb-8 flex-1">
                    {p.features.map((f) => (
                      <li key={f.text} className="flex items-center gap-3 text-sm mb-3">
                        {f.included ? (
                          <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#4ade80" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                        ) : (
                          <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#374151" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                        )}
                        <span className={f.included ? "text-gray-300" : "text-gray-600"}>{f.text}</span>
                      </li>
                    ))}
                  </ul>
                  <Link to={p.href} className={`block text-center py-3.5 rounded-xl font-semibold text-sm transition-colors ${p.popular ? "bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-400 hover:to-red-500" : "bg-gray-800/60 text-gray-300 border border-gray-700/30 hover:bg-gray-800"}`}>
                    {p.cta}
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-20 border-t border-gray-800/50">
          <div className="landing-section-sm">
            <div className="text-center mb-14">
              <p className="text-sm font-semibold text-red-400 uppercase tracking-widest mb-3">Preguntas frecuentes</p>
              <h2 className="text-3xl font-bold">¿Tenés dudas?</h2>
            </div>
            <div className="flex flex-col gap-3">
              {FAQ.map((item) => (
                <details key={item.q} className="rounded-xl bg-gray-900/40 border border-gray-800/60 overflow-hidden">
                  <summary className="px-6 py-5 cursor-pointer text-sm font-medium flex items-center justify-between list-none hover:bg-gray-800/30 transition-colors">
                    {item.q}
                    <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#6b7280" strokeWidth="2" className="shrink-0 ml-4">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                    </svg>
                  </summary>
                  <div className="px-6 pb-5 text-sm text-gray-400 leading-relaxed">{item.a}</div>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20">
          <div className="landing-section-md">
            <div className="rounded-2xl bg-gradient-to-b from-red-500/10 to-gray-900/80 border border-red-500/20 py-12 sm:py-16 px-6 sm:px-8 text-center">
              <h2 className="text-3xl font-bold mb-4">Empezá a ahorrar hoy</h2>
              <p className="text-gray-400 max-w-md mx-auto mb-8">Unite a miles de cazadores de ofertas que ya usan Howlify.</p>
              <Link to="/register" className="inline-block px-10 py-4 bg-white text-gray-950 rounded-xl font-semibold text-base hover:bg-gray-100 transition-colors">
                Crear cuenta gratis
              </Link>
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="border-t border-gray-800/50">
          <div className="max-w-7xl mx-auto px-6 py-8 flex flex-wrap items-center justify-between gap-4 text-sm text-gray-500">
            <span>© 2026 Howlify. Todos los derechos reservados.</span>
            <div className="flex items-center gap-5">
              <Link to="/terms" className="hover:text-white transition-colors">Términos</Link>
              <Link to="/privacy" className="hover:text-white transition-colors">Privacidad</Link>
              <a href="mailto:howlify.app@gmail.com" className="hover:text-white transition-colors">Contacto</a>
            </div>
          </div>
        </footer>

      </div>
    </PageTransition>
  );
}
