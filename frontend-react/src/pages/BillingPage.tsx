import PageTransition from "../components/PageTransition";

const PLAN_LABELS: Record<string, string> = {
  starter: "Starter",
  pro: "Pro",
  business_reseller: "Business Reseller",
  business_monitor: "Business Monitor",
};

export default function BillingPage() {
  return (
    <PageTransition>
      <div className="p-4 md:p-8 space-y-8">
        <div>
          <h2 className="text-xl font-bold text-white">💳 Facturación</h2>
          <p className="text-sm text-gray-500">Próximamente — pagos con Mercado Pago</p>
        </div>

        <div className="bg-gradient-to-br from-yellow-500/10 to-yellow-600/5 rounded-2xl p-8 text-center border border-yellow-500/20">
          <div className="text-5xl mb-4">🚀</div>
          <h3 className="text-xl font-bold text-white mb-2">Howlify en beta gratuita</h3>
          <p className="text-gray-400 max-w-md mx-auto">
            Durante esta etapa todas las funciones están disponibles sin costo.
            Cuando la app esté lista para lanzar al público, activaremos los planes de pago.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            {Object.entries(PLAN_LABELS).map(([key, label]) => (
              <span key={key} className="px-3 py-1.5 bg-gray-800/50 rounded-full text-xs text-gray-400 border border-gray-700/50">
                {label} {key === "starter" ? "🆓" : "🔒"}
              </span>
            ))}
          </div>
          <p className="text-xs text-gray-600 mt-4">
            Para activar: <code className="text-yellow-500/80 bg-yellow-500/10 px-1 rounded">PAYMENT_ENABLED=true</code>
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
