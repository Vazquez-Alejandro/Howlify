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
  return (
    <PageTransition>
      <div style={{ minHeight: "100vh", background: "#030712", color: "#f3f4f6" }}>

        {/* NAV */}
        <nav style={{ position: "relative", zIndex: 10, display: "flex", alignItems: "center", justifyContent: "space-between", maxWidth: "72rem", marginLeft: "auto", marginRight: "auto", padding: "1.25rem 1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <Logo size="md" />
            <span style={{ fontSize: "1.25rem", fontWeight: 700 }}>Howlify</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <Link to="/login" style={{ padding: "0.5rem 1rem", fontSize: "0.875rem", fontWeight: 500, color: "#9ca3af" }}>Iniciar Sesión</Link>
            <Link to="/register" style={{ padding: "0.625rem 1.25rem", fontSize: "0.875rem", fontWeight: 600, background: "#fff", color: "#030712", borderRadius: "0.75rem" }}>Empezar gratis</Link>
          </div>
        </nav>

        {/* HERO */}
        <section style={{ position: "relative", zIndex: 10, maxWidth: "56rem", marginLeft: "auto", marginRight: "auto", padding: "5rem 1.5rem 6rem", textAlign: "center" }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", padding: "0.375rem 1rem", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "9999px", fontSize: "0.875rem", color: "#f87171", marginBottom: "2rem" }}>
            <span style={{ width: "0.5rem", height: "0.5rem", borderRadius: "50%", background: "#ef4444" }} />
            Monitoreo de precios en tiempo real
          </div>
          <h1 style={{ fontSize: "clamp(2.5rem, 6vw, 4.5rem)", fontWeight: 800, lineHeight: 1.1, letterSpacing: "-0.02em" }}>
            Nunca más te pierdas{" "}
            <span style={{ background: "linear-gradient(to right, #f87171, #dc2626)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>una oferta</span>
          </h1>
          <p style={{ marginTop: "1.75rem", fontSize: "1.125rem", color: "#9ca3af", maxWidth: "40rem", marginLeft: "auto", marginRight: "auto", lineHeight: 1.7 }}>
            Howlify monitorea precios 24/7 en MercadoLibre y tiendas online.
            Recibí alertas al instante cuando haya ofertas o el precio que buscás.
          </p>
          <div style={{ marginTop: "2.5rem", display: "flex", justifyContent: "center", gap: "1rem", flexWrap: "wrap" }}>
            <Link to="/register" style={{ padding: "1rem 2rem", background: "#fff", color: "#030712", borderRadius: "0.75rem", fontWeight: 600, fontSize: "1rem" }}>
              Empezar gratis — 7 días
            </Link>
            <Link to="/login" style={{ padding: "1rem 2rem", background: "rgba(31,41,55,0.6)", border: "1px solid rgba(75,85,99,0.5)", color: "#d1d5db", borderRadius: "0.75rem", fontWeight: 600, fontSize: "1rem" }}>
              Ya tengo cuenta
            </Link>
          </div>
          <div style={{ marginTop: "4rem", display: "flex", justifyContent: "center", gap: "3rem", fontSize: "0.875rem", color: "#6b7280" }}>
            <div style={{ textAlign: "center" }}>
              <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#fff" }}><CountUp target={1200} />+</p>
              <p style={{ marginTop: "0.25rem" }}>Cacerías activas</p>
            </div>
            <div style={{ width: "1px", background: "#1f2937" }} />
            <div style={{ textAlign: "center" }}>
              <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#fff" }}><CountUp target={50} />K+</p>
              <p style={{ marginTop: "0.25rem" }}>Alertas enviadas</p>
            </div>
            <div style={{ width: "1px", background: "#1f2937" }} />
            <div style={{ textAlign: "center" }}>
              <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "#fff" }}>24/7</p>
              <p style={{ marginTop: "0.25rem" }}>Monitoreo activo</p>
            </div>
          </div>
        </section>

        {/* CÓMO FUNCIONA */}
        <section style={{ padding: "5rem 0" }}>
          <div className="landing-section-md" style={{ textAlign: "center" }}>
            <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#f87171", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.75rem" }}>Simple y automático</p>
            <h2 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "3.5rem" }}>Cómo funciona</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "2rem" }}>
              {STEPS.map((s) => (
                <div key={s.num} style={{ textAlign: "center" }}>
                  <div style={{ width: "3rem", height: "3rem", borderRadius: "1rem", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1.25rem" }}>
                    <span style={{ color: "#f87171", fontWeight: 700, fontSize: "1.125rem" }}>{s.num}</span>
                  </div>
                  <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>{s.title}</h3>
                  <p style={{ fontSize: "0.875rem", color: "#6b7280", lineHeight: 1.6 }}>{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section style={{ padding: "5rem 0", borderTop: "1px solid rgba(31,41,55,0.5)" }}>
          <div className="landing-section">
            <div style={{ textAlign: "center", marginBottom: "3.5rem" }}>
              <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#f87171", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.75rem" }}>Funcionalidades</p>
              <h2 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "1rem" }}>Todo lo que necesitás</h2>
              <p style={{ color: "#9ca3af", maxWidth: "36rem", marginLeft: "auto", marginRight: "auto" }}>Monitoreo inteligente, alertas instantáneas, historial de precios.</p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.5rem" }}>
              {FEATURES.map((f) => (
                <div key={f.title} style={{ padding: "1.5rem", borderRadius: "1rem", background: "rgba(17,24,39,0.4)", border: "1px solid rgba(31,41,55,0.6)" }}>
                  <div style={{ width: "2.75rem", height: "2.75rem", borderRadius: "0.75rem", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", display: "flex", alignItems: "center", justifyContent: "center", color: "#f87171", marginBottom: "1.25rem" }}>
                    {ICONS[f.icon]}
                  </div>
                  <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>{f.title}</h3>
                  <p style={{ fontSize: "0.875rem", color: "#6b7280", lineHeight: 1.6 }}>{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* PRICING */}
        <section style={{ padding: "5rem 0", borderTop: "1px solid rgba(31,41,55,0.5)" }}>
          <div className="landing-section-md">
            <div style={{ textAlign: "center", marginBottom: "3.5rem" }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", padding: "0.375rem 1rem", background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.2)", borderRadius: "9999px", fontSize: "0.875rem", color: "#4ade80", marginBottom: "1.25rem" }}>
                7 días gratis · Sin tarjeta de crédito
              </div>
              <h2 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "1rem" }}>Elegí tu rango en la manada</h2>
              <p style={{ color: "#9ca3af" }}>Empezá gratis, escalá cuando lo necesites.</p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1.5rem" }}>
              {PLANS.map((p) => (
                <div key={p.name} style={{
                  position: "relative", borderRadius: "1rem", padding: "2rem", display: "flex", flexDirection: "column",
                  border: p.popular ? "1px solid rgba(239,68,68,0.3)" : "1px solid rgba(31,41,55,0.6)",
                  background: p.popular ? "linear-gradient(to bottom, rgba(239,68,68,0.08), rgba(17,24,39,0.8))" : "rgba(17,24,39,0.4)",
                }}>
                  {p.popular && (
                    <div style={{ position: "absolute", top: "-0.75rem", left: "50%", transform: "translateX(-50%)", padding: "0.25rem 1rem", background: "linear-gradient(to right, #ef4444, #dc2626)", borderRadius: "9999px", fontSize: "0.75rem", fontWeight: 600, color: "#fff", whiteSpace: "nowrap" }}>
                      Más popular
                    </div>
                  )}
                  <h3 style={{ fontSize: "1.25rem", fontWeight: 700 }}>{p.name}</h3>
                  <p style={{ fontSize: "0.875rem", color: "#6b7280", marginTop: "0.25rem" }}>{p.desc}</p>
                  <div style={{ marginTop: "1.5rem", marginBottom: "2rem" }}>
                    <span style={{ fontSize: "3rem", fontWeight: 800 }}>${p.price}</span>
                    <span style={{ color: "#6b7280", fontSize: "0.875rem", marginLeft: "0.25rem" }}>/mes</span>
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: "0 0 2rem 0", flex: 1 }}>
                    {p.features.map((f) => (
                      <li key={f.text} style={{ display: "flex", alignItems: "center", gap: "0.75rem", fontSize: "0.875rem", marginBottom: "0.75rem" }}>
                        {f.included ? (
                          <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#4ade80" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                        ) : (
                          <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#374151" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                        )}
                        <span style={{ color: f.included ? "#d1d5db" : "#4b5563" }}>{f.text}</span>
                      </li>
                    ))}
                  </ul>
                  <Link to={p.href} style={{
                    display: "block", textAlign: "center", padding: "0.875rem", borderRadius: "0.75rem", fontWeight: 600, fontSize: "0.875rem",
                    background: p.popular ? "linear-gradient(to right, #ef4444, #dc2626)" : "rgba(31,41,55,0.6)",
                    color: p.popular ? "#fff" : "#d1d5db",
                    border: p.popular ? "none" : "1px solid rgba(75,85,99,0.3)",
                  }}>
                    {p.cta}
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section style={{ padding: "5rem 0", borderTop: "1px solid rgba(31,41,55,0.5)" }}>
          <div className="landing-section-sm">
            <div style={{ textAlign: "center", marginBottom: "3.5rem" }}>
              <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#f87171", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.75rem" }}>Preguntas frecuentes</p>
              <h2 style={{ fontSize: "2rem", fontWeight: 700 }}>¿Tenés dudas?</h2>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {FAQ.map((item) => (
                <details key={item.q} style={{ borderRadius: "1rem", background: "rgba(17,24,39,0.4)", border: "1px solid rgba(31,41,55,0.6)", overflow: "hidden" }}>
                  <summary style={{ padding: "1.25rem 1.5rem", cursor: "pointer", fontSize: "0.875rem", fontWeight: 500, display: "flex", alignItems: "center", justifyContent: "space-between", listStyle: "none" }}>
                    {item.q}
                    <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#6b7280" strokeWidth="2" style={{ flexShrink: 0, marginLeft: "1rem" }}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                    </svg>
                  </summary>
                  <div style={{ padding: "0 1.5rem 1.25rem", fontSize: "0.875rem", color: "#9ca3af", lineHeight: 1.6 }}>{item.a}</div>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section style={{ padding: "5rem 0" }}>
          <div className="landing-section-md">
            <div style={{ borderRadius: "1.5rem", background: "linear-gradient(to bottom, rgba(239,68,68,0.1), rgba(17,24,39,0.8))", border: "1px solid rgba(239,68,68,0.2)", padding: "4rem 2rem", textAlign: "center" }}>
              <h2 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "1rem" }}>Empezá a ahorrar hoy</h2>
              <p style={{ color: "#9ca3af", maxWidth: "28rem", marginLeft: "auto", marginRight: "auto", marginBottom: "2rem" }}>Unite a miles de cazadores de ofertas que ya usan Howlify.</p>
              <Link to="/register" style={{ display: "inline-block", padding: "1rem 2.5rem", background: "#fff", color: "#030712", borderRadius: "0.75rem", fontWeight: 600, fontSize: "1rem" }}>
                Crear cuenta gratis
              </Link>
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer style={{ borderTop: "1px solid rgba(31,41,55,0.5)" }}>
          <div style={{ maxWidth: "72rem", marginLeft: "auto", marginRight: "auto", padding: "2rem 1.5rem", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", fontSize: "0.875rem", color: "#6b7280" }}>
            <span>© 2026 Howlify. Todos los derechos reservados.</span>
            <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
              <Link to="/terms">Términos</Link>
              <Link to="/privacy">Privacidad</Link>
              <a href="mailto:howlify.app@gmail.com">Contacto</a>
            </div>
          </div>
        </footer>

      </div>
    </PageTransition>
  );
}
