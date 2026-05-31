import { useState, useEffect } from "react";

interface Step {
  icon: string;
  title: string;
  description: string;
  tip?: string;
}

const STEPS: Step[] = [
  {
    icon: "🐺",
    title: "Bienvenido a Howlify",
    description: "Te voy a guiar para que empieces a olfatear ofertas en minutos. Son solo 4 pasos.",
  },
  {
    icon: "🔍",
    title: "Creá una cacería",
    description: "Presioná el botón para agregar un producto que querés monitorear. Podes buscar por keyword o pegar un link directo de Mercado Libre.",
    tip: "+ Nueva Cacería",
  },
  {
    icon: "🐾",
    title: "Olfateá ofertas",
    description: "Cada cacería tiene un botón de olfateo. Presionalo para buscar ofertas automáticamente. Los resultados aparecen con precio y link directo.",
  },
  {
    icon: "⚡",
    title: "Interpretá las alertas",
    description: "Si el precio baja de tu límite, verás una etiqueta de alerta. Así sabés al toque cuándo conviene comprar.",
    tip: "ALERTA",
  },
  {
    icon: "⚙️",
    title: "Configurá tu perfil",
    description: "En Configuración podes cambiar contraseña, email y preferencias de notificación. También podes ver tu plan en Facturación.",
  },
];

const STORAGE_KEY = "howlify_onboarding_done";

function StepIndicator({ total, current }: { total: number; current: number }) {
  return (
    <div className="flex gap-1.5 justify-center">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`h-1.5 rounded-full transition-all duration-500 ease-out ${
            i < current ? "bg-red-500 w-6" : i === current ? "bg-red-500 w-8" : "bg-gray-700 w-3"
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

  const handlePrev = () => {
    if (step > 0) setStep(step - 1);
  };

  const finish = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setStep(-1);
  };

  if (step < 0) return null;

  const s = STEPS[step];
  const isWelcome = step === 0;
  const isLast = step === STEPS.length - 1;
  const progress = ((step) / (STEPS.length - 1)) * 100;

  return (
    <>
      <div
        className="fixed inset-0 z-[9999] bg-black/70 backdrop-blur-sm"
        onClick={finish}
      />

      <div className="fixed inset-0 z-[10000] flex items-center justify-center p-5">
        <div
          className="bg-gray-900 rounded-2xl shadow-2xl pointer-events-auto overflow-hidden border border-gray-700/40"
          style={{ width: "380px" }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Top progress bar */}
          <div className="h-1 bg-gray-800">
            <div
              className="h-full bg-gradient-to-r from-red-600 to-red-400 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Content wrapper with fixed height */}
          <div className="flex flex-col" style={{ minHeight: "340px" }}>
            <div className="flex-1 flex flex-col justify-between p-7">
              {/* Step indicator */}
              {!isWelcome && (
                <div className="mb-5">
                  <StepIndicator total={STEPS.length - 1} current={step - 1} />
                </div>
              )}

              {/* Icon */}
              <div className="flex justify-center mb-5">
                <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/15 flex items-center justify-center">
                  <span className="text-2xl">{s.icon}</span>
                </div>
              </div>

              {/* Title + description */}
              <div className="text-center flex-1">
                <h2 className="text-lg font-bold text-white mb-2">{s.title}</h2>
                <p className="text-sm text-gray-400 leading-relaxed">{s.description}</p>
                {s.tip && (
                  <div className="inline-block mt-3 px-4 py-1.5 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <span className="text-sm font-semibold text-red-400">{s.tip}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Buttons - always at bottom */}
            <div className="px-7 pb-7">
              <div className="flex items-center gap-2 pt-4 border-t border-gray-800/50">
                {!isWelcome && (
                  <button
                    onClick={handlePrev}
                    className="px-3 py-2.5 bg-gray-800/60 text-gray-400 rounded-xl text-xs font-medium hover:bg-gray-700/60 hover:text-gray-200 transition-all border border-gray-700/40 whitespace-nowrap"
                  >
                    Atrás
                  </button>
                )}
                <button
                  onClick={finish}
                  className="px-3 py-2.5 text-gray-500 hover:text-gray-300 text-xs transition-colors whitespace-nowrap"
                >
                  Saltar
                </button>
                <button
                  onClick={isLast ? finish : handleNext}
                  className="flex-1 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl text-xs font-semibold hover:from-red-600 hover:to-red-700 transition-all shadow-lg shadow-red-500/20 active:scale-[0.98]"
                >
                  {isWelcome ? "Empezar" : isLast ? "Listo" : "Siguiente"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
