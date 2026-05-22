import { Link } from "react-router-dom";
import PageTransition from "../components/PageTransition";

export default function TermsPage() {
  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-950 px-4 py-12">
        <div className="max-w-2xl mx-auto">
          <Link to="/register" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-red-400 transition-colors mb-8">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            Volver
          </Link>
          <div className="bg-gray-900/60 rounded-2xl p-8 md:p-10 border border-gray-800/50">
            <h1 className="text-2xl font-bold text-white mb-6">Términos y Condiciones</h1>
            <p className="text-sm text-gray-500 mb-6">Última actualización: mayo 2026</p>

            <div className="space-y-6 text-sm text-gray-400 leading-relaxed">
              <section>
                <h2 className="text-base font-semibold text-white mb-2">1. Aceptación de los términos</h2>
                <p>Al crear una cuenta y utilizar Howlify ("la Plataforma"), aceptás los presentes Términos y Condiciones. Si no estás de acuerdo, no uses el servicio.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">2. Descripción del servicio</h2>
                <p>Howlify es una plataforma de monitoreo de precios que permite a los usuarios rastrear productos, vuelos y alojamientos en tiendas online. La Plataforma extrae información pública disponible en internet y la organiza para facilitar su análisis.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">3. Cuentas y responsabilidad del usuario</h2>
                <p>Sos responsable de mantener la confidencialidad de tu contraseña y de toda actividad que ocurra en tu cuenta. No podés usar la Plataforma para actividades ilegales o no autorizadas.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">4. Planes y facturación</h2>
                <p>Howlify ofrece planes gratuitos (con límite de prueba) y planes pagos. Los precios y características están detallados en la sección de Facturación. Podés cancelar tu suscripción en cualquier momento desde el portal de facturación. Los reembolsos se gestionan caso por caso.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">5. Uso aceptable</h2>
                <p>No debes:</p>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li>Realizar solicitudes excesivas que degraden el servicio</li>
                  <li>Usar la Plataforma para monitorear precios con fines ilegales</li>
                  <li>Intentar vulnerar la seguridad del sistema</li>
                  <li>Revender o redistribuir los datos obtenidos sin autorización</li>
                </ul>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">6. Limitación de responsabilidad</h2>
                <p>Howlify no garantiza la exactitud, integridad o actualidad de los precios mostrados. La información se proporciona "tal cual" y puede contener errores. No nos hacemos responsables por decisiones comerciales basadas en los datos de la Plataforma.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">7. Modificaciones</h2>
                <p>Nos reservamos el derecho de modificar estos términos en cualquier momento. Los cambios serán notificados por email y/o mediante un aviso en la Plataforma. El uso continuado del servicio después de los cambios constituye la aceptación de los nuevos términos.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">8. Contacto</h2>
                <p>Para consultas sobre estos términos, contactanos a <a href="mailto:soporte@howlify.app" className="text-red-400 hover:text-red-300 underline underline-offset-2">soporte@howlify.app</a>.</p>
              </section>
            </div>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
