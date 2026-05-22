import { useState, useEffect } from "react";

interface Step {
  title: string;
  description: string;
  target?: string;
  position?: "bottom" | "top";
}

const STEPS: Step[] = [
  {
    title: "🐺 Bienvenido a Howlify",
    description: "Te voy a guiar para que empieces a olfatear ofertas en minutos. Son solo 4 pasos.",
  },
  {
    title: "1. Creá una cacería",
    description: "Presioná el botón '+ Nueva Cacería' para agregar un producto, vuelo o alojamiento que querés monitorear.",
    target: "#new-caza-btn",
    position: "top",
  },
  {
    title: "2. Olfateá",
    description: "Cada cacería tiene un botón 🐺. Presionalo para buscar ofertas automáticamente. Los resultados aparecen abajo con precio y link directo.",
  },
  {
    title: "3. Interpretá las alertas",
    description: "Si el precio baja de tu límite, verás una etiqueta roja 'ALERTA'. Un badge amarillo 'ERROR PRECIO' indica un precio anómalamente bajo.",
  },
  {
    title: "4. Configurá tu perfil",
    description: "En la sección Configuración podés cambiar contraseña, email y preferencias de notificación. También podés ver tu plan actual en Facturación.",
  },
];

const STORAGE_KEY = "howlify_onboarding_done";

export default function OnboardingTour() {
  const [step, setStep] = useState(-1);

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      setTimeout(() => setStep(0), 600);
    }
  }, []);

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      finish();
    }
  };

  const finish = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setStep(-1);
  };

  if (step < 0) return null;

  const s = STEPS[step];
  const isWelcome = step === 0;
  const isLast = step === STEPS.length - 1;
  const hasTarget = !!s.target;

  return (
    <>
      <div className="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-sm" onClick={finish} />

      <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4 pointer-events-none">
        <div
          className={`bg-gray-900 border border-red-500/30 rounded-3xl p-6 shadow-2xl w-full pointer-events-auto ${hasTarget ? "max-w-xs" : "max-w-md"}`}
          onClick={(e) => e.stopPropagation()}
          style={hasTarget ? { marginTop: "-20vh" } : {}}
        >
          {!isWelcome && (
            <div className="flex gap-1.5 mb-4">
              {STEPS.slice(1).map((_, i) => (
                <div key={i} className={`flex-1 h-1 rounded-full ${i <= step - 1 ? "bg-red-500" : "bg-gray-700"}`} />
              ))}
            </div>
          )}

          {isWelcome ? (
            <div className="text-center">
              <div className="text-5xl mb-3">🐺</div>
              <h2 className="text-xl font-bold text-white">{s.title}</h2>
              <p className="text-sm text-gray-400 mt-3 leading-relaxed">{s.description}</p>
              <div className="flex gap-3 mt-6">
                <button onClick={handleNext} className="flex-1 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold hover:from-red-600 hover:to-red-700 transition-all shadow-lg shadow-red-500/20">
                  Empezar
                </button>
                <button onClick={finish} className="px-6 py-2.5 bg-gray-800/50 text-gray-400 rounded-xl hover:bg-gray-700/50 hover:text-gray-200 transition-all border border-gray-700/50">
                  Saltar
                </button>
              </div>
            </div>
          ) : (
            <div>
              <h3 className="text-sm font-bold text-white mb-2">{s.title}</h3>
              <p className="text-xs text-gray-400 leading-relaxed">{s.description}</p>
              {hasTarget && (
                <p className="text-[10px] text-red-400/70 mt-2 italic">Hacé clic afuera para saltar</p>
              )}
              <div className="flex items-center justify-between mt-4">
                <button onClick={finish} className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2 py-1">
                  Saltar
                </button>
                <button onClick={isLast ? finish : handleNext} className="px-4 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/30 transition-all border border-red-500/20">
                  {isLast ? "Listo 🚀" : "Siguiente →"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
