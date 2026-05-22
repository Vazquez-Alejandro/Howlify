import { useState, useEffect } from "react";

interface Step {
  title: string;
  description: string;
  highlight?: string;
}

const STEPS: Step[] = [
  {
    title: "🐺 Bienvenido a Howlify",
    description: "Te voy a guiar para que empieces a olfatear ofertas en minutos. Son solo 4 pasos.",
  },
  {
    title: "1. Creá una cacería",
    description: "Presioná el botón",
    highlight: "'+ Nueva Cacería'",
  },
  {
    title: "2. Olfateá",
    description: "Cada cacería tiene un botón 🐺. Presionalo para buscar ofertas automáticamente. Los resultados aparecen abajo con precio y link directo.",
  },
  {
    title: "3. Interpretá las alertas",
    description: "Si el precio baja de tu límite, verás una etiqueta roja",
    highlight: "ALERTA",
  },
  {
    title: "4. Configurá tu perfil",
    description: "En la sección Configuración podés cambiar contraseña, email y preferencias de notificación. También podés ver tu plan actual en Facturación.",
  },
];

const STORAGE_KEY = "howlify_onboarding_done";

function StepIndicator({ total, current }: { total: number; current: number }) {
  return (
    <div className="flex gap-2 justify-center">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`h-2 rounded-full transition-all duration-300 ${
            i <= current ? "bg-red-500 w-6" : "bg-gray-700 w-2"
          }`}
        />
      ))}
    </div>
  );
}

export default function OnboardingTour() {
  const [step, setStep] = useState(-1);

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      setTimeout(() => setStep(0), 500);
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

  return (
    <>
      <div className="fixed inset-0 z-[9999] bg-black/70 backdrop-blur-sm" onClick={finish} />

      <div className="fixed inset-0 z-[10000] flex items-center justify-center p-6">
        <div
          className="bg-gray-900 border border-gray-700/50 rounded-3xl shadow-2xl w-full max-w-md pointer-events-auto overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header gradient */}
          <div className="h-1.5 bg-gradient-to-r from-red-600 via-red-500 to-red-400" />

          <div className="px-7 py-6">
            {!isWelcome && (
              <div className="mb-5">
                <StepIndicator total={STEPS.length - 1} current={step - 1} />
              </div>
            )}

            {isWelcome ? (
              <div className="text-center">
                <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">🐺</span>
                </div>
                <h2 className="text-xl font-bold text-white mb-3">{s.title}</h2>
                <p className="text-sm text-gray-400 leading-relaxed">{s.description}</p>
                <div className="flex gap-3 mt-7">
                  <button
                    onClick={handleNext}
                    className="flex-1 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold text-sm hover:from-red-600 hover:to-red-700 transition-all shadow-lg shadow-red-500/25 active:scale-[0.98]"
                  >
                    Empezar
                  </button>
                  <button
                    onClick={finish}
                    className="px-6 py-3 bg-gray-800/50 text-gray-400 rounded-xl text-sm hover:bg-gray-700/50 hover:text-gray-200 transition-all border border-gray-700/50"
                  >
                    Saltar
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <h3 className="text-base font-bold text-white mb-3">{s.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  {s.description}{" "}
                  {s.highlight && (
                    <span className="inline-block mt-2 px-3 py-1 bg-red-500/15 text-red-400 rounded-lg text-sm font-semibold border border-red-500/20">
                      {s.highlight}
                    </span>
                  )}
                </p>
                <div className="flex items-center justify-between mt-7 pt-4 border-t border-gray-800/50">
                  <button
                    onClick={finish}
                    className="text-sm text-gray-500 hover:text-gray-300 transition-colors px-2 py-1"
                  >
                    Saltar
                  </button>
                  <button
                    onClick={isLast ? finish : handleNext}
                    className="px-5 py-2 bg-red-500/15 text-red-400 rounded-xl text-sm font-semibold hover:bg-red-500/25 transition-all border border-red-500/20 active:scale-[0.98]"
                  >
                    {isLast ? "Listo 🚀" : "Siguiente →"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
