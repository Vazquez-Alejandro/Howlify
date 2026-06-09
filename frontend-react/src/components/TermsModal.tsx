import { Link } from "react-router-dom";
import PageTransition from "./PageTransition";

interface Props {
  onAccept?: () => void;
  readonly?: boolean;
}

export default function TermsModal({ onAccept, readonly = false }: Props) {
  return (
    <div className="fixed inset-0 z-[9999] bg-gray-950 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {!readonly && (
          <p className="text-xs text-gray-600 text-center mb-4">
            Debés aceptar los Términos y Condiciones para usar Howlify
          </p>
        )}

        <div className="bg-gray-900/80 rounded-2xl p-6 md:p-8 border border-gray-800/50">
          <h1 className="text-xl font-bold text-white mb-1">Términos y Condiciones</h1>
          <p className="text-xs text-gray-500 mb-5">Última actualización: junio 2026</p>

          <div className="space-y-5 text-sm text-gray-400 leading-relaxed">
            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">1. Aceptación de los términos</h2>
              <p>Al crear una cuenta y utilizar Howlify ("la Plataforma"), aceptás los presentes Términos y Condiciones. Si no estás de acuerdo, no uses el servicio. El uso continuado de la Plataforma constituye la aceptación plena de estos términos.</p>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">2. Descripción del servicio</h2>
              <p>Howlify es una plataforma de monitoreo de precios que permite a los usuarios rastrear productos, vuelos y alojamientos en tiendas online. La Plataforma extrae información pública disponible en internet y la organiza para facilitar su análisis.</p>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">3. Cuentas y responsabilidad del usuario</h2>
              <p>Sos responsable de mantener la confidencialidad de tu contraseña y de toda actividad que ocurra en tu cuenta. Te comprometés a:</p>
              <ul className="list-disc pl-5 mt-1.5 space-y-1">
                <li>No usar la Plataforma para actividades ilegales, fraudulentas o no autorizadas</li>
                <li>No intentar acceder a cuentas de otros usuarios</li>
                <li>No transmitir virus, malware o código dañino</li>
                <li>No realizar solicitudes automatizadas masivas que degraden el servicio</li>
                <li>No usar los datos obtenidos para competir directamente con Howlify</li>
              </ul>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">4. Planes y facturación</h2>
              <p>Howlify ofrece planes gratuitos y planes pagos con diferentes niveles de acceso. Los precios y características están detallados en la sección de Facturación. Podés cancelar tu suscripción en cualquier momento. Los reembolsos se gestionan caso por caso. Los precios están expresados en pesos argentinos (ARS) y pueden variar sin previo aviso.</p>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">5. Uso aceptable</h2>
              <p>Queda estrictamente prohibido:</p>
              <ul className="list-disc pl-5 mt-1.5 space-y-1">
                <li>Revender, redistribuir o explotar comercialmente los datos obtenidos</li>
                <li>Usar la Plataforma para fines de ingeniería inversa o competencia desleal</li>
                <li>Manipular o falsificar headers de solicitud para evadir límites</li>
                <li>Compartir credenciales de acceso con terceros</li>
                <li>Usar bots o scripts automatizados fuera de la funcionalidad habitual del servicio</li>
              </ul>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">6. Limitación de responsabilidad</h2>
              <p>Howlify no garantiza la exactitud, integridad o actualidad de los precios mostrados. La información se proporciona "tal cual" y puede contener errores. Los datos provienen de fuentes públicas de terceros y pueden no estar actualizados en tiempo real.</p>
              <p className="mt-1.5">En ningún caso Howlify, su titular o sus proveedores serán responsables por:</p>
              <ul className="list-disc pl-5 mt-1.5 space-y-1">
                <li>Decisiones comerciales, financieras o de compra basadas en los datos de la Plataforma</li>
                <li>Pérdidas de beneficios, datos o oportunidades comerciales</li>
                <li>Daños indirectos, incidentales o consecuentes</li>
                <li>Interrupciones del servicio o errores en los datos</li>
              </ul>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">7. Propiedad intelectual</h2>
              <p>El código fuente, diseño, marca, logotipo y contenido original de Howlify son propiedad de Alejandro Vázquez y están protegidos por las leyes de propiedad intelectual. Queda prohibida su reproducción total o parcial sin autorización expresa.</p>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">8. Suspensión y terminación</h2>
              <p>Nos reservamos el derecho de suspender o eliminar tu cuenta sin previo aviso si violás estos términos o si detectamos uso indebido de la Plataforma. En caso de suspensión, no tendrás derecho a reembolso por pagos ya realizados.</p>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">9. Modificaciones</h2>
              <p>Nos reservamos el derecho de modificar estos términos en cualquier momento. Los cambios sustanciales serán notificados por email con al menos 15 días de anticipación. El uso continuado del servicio después de los cambios constituye la aceptación de los nuevos términos.</p>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">10. Ley aplicable y jurisdicción</h2>
              <p>Estos términos se rigen por las leyes de la República Argentina. Cualquier controversia será sometida a los tribunales ordinarios de la Ciudad Autónoma de Buenos Aires.</p>
            </section>

            <section>
              <h2 className="text-sm font-semibold text-white mb-1.5">11. Contacto</h2>
              <p>Titular: Alejandro Vázquez (CUIT 20-29479657-7)</p>
              <p>Consultas: <a href="mailto:howlify.app@gmail.com" className="text-red-400 hover:text-red-300 underline underline-offset-2">howlify.app@gmail.com</a></p>
            </section>
          </div>

          {!readonly && onAccept && (
            <div className="mt-8 pt-5 border-t border-gray-800/50">
              <button
                onClick={onAccept}
                className="w-full py-3.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold text-sm hover:from-red-600 hover:to-red-700 transition-all"
              >
                He leído y acepto los Términos y Condiciones
              </button>
              <p className="text-[11px] text-gray-600 text-center mt-3">
                Al hacer click aceptás nuestros{" "}
                <Link to="/terms" className="text-gray-500 hover:text-red-400 underline underline-offset-2">Términos</Link>
                {" y "}
                <Link to="/privacy" className="text-gray-500 hover:text-red-400 underline underline-offset-2">Política de Privacidad</Link>
              </p>
            </div>
          )}

          {readonly && (
            <div className="mt-6 pt-4 border-t border-gray-800/50 text-center">
              <Link to="/dashboard" className="text-sm text-gray-500 hover:text-white transition-colors">
                Volver al dashboard
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
