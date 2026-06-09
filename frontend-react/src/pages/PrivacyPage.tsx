import { Link } from "react-router-dom";
import PageTransition from "../components/PageTransition";

export default function PrivacyPage() {
  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-950 px-4 py-12">
        <div className="max-w-2xl mx-auto">
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-red-400 transition-colors mb-8">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            Volver
          </Link>
          <div className="bg-gray-900/60 rounded-2xl p-8 md:p-10 border border-gray-800/50">
            <h1 className="text-2xl font-bold text-white mb-2">Política de Privacidad</h1>
            <p className="text-sm text-gray-500 mb-6">Última actualización: junio 2026 · Conforme a Ley 25.326 de Protección de Datos Personales (Argentina)</p>

            <div className="space-y-6 text-sm text-gray-400 leading-relaxed">
              <section>
                <h2 className="text-base font-semibold text-white mb-2">1. Responsable del tratamiento</h2>
                <p><strong>Alejandro Vázquez</strong> (CUIT 20-29479657-7) es el responsable del tratamiento de los datos personales recopilados a través de Howlify.</p>
                <p>Contacto: <a href="mailto:howlify.app@gmail.com" className="text-red-400 hover:text-red-300 underline underline-offset-2">howlify.app@gmail.com</a></p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">2. Datos que recopilamos</h2>
                <p>Recopilamos la siguiente información cuando creás una cuenta:</p>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li>Dirección de email</li>
                  <li>Nombre de usuario</li>
                  <li>Plan de suscripción seleccionado</li>
                  <li>Preferencias de notificación (WhatsApp, Telegram, email)</li>
                </ul>
                <p className="mt-2">También almacenamos las URLs de productos que monitoreás, el historial de precios asociado, y configuraciones de alertas personalizadas.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">3. Finalidad del tratamiento</h2>
                <p>Usamos tus datos para:</p>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li>Proveer y mantener el servicio de monitoreo de precios</li>
                  <li>Enviar alertas de precios según tus preferencias</li>
                  <li>Generar reportes y análisis de precios</li>
                  <li>Gestionar tu cuenta y facturación</li>
                  <li>Comunicarnos sobre cambios en el servicio</li>
                </ul>
                <p className="mt-2">La base legal para el tratamiento es la prestación del consentimiento al crear tu cuenta y la ejecución del contrato de servicio.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">4. Almacenamiento y seguridad</h2>
                <p>Tus datos se almacenan en servidores de Supabase (PostgreSQL) con cifrado en tránsito (TLS) y en reposo. Implementamos medidas de seguridad técnicas y organizativas para proteger tu información contra accesos no autorizados, pérdida o alteración.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">5. Compartición de datos</h2>
                <p>No vendemos ni compartimos tus datos personales con terceros.</p>
                <p className="mt-2">Usamos los siguientes servicios de terceros que procesan datos en nuestro nombre:</p>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li><strong>Supabase</strong> — Base de datos y autenticación</li>
                  <li><strong>Resend</strong> — Envío de emails transaccionales</li>
                  <li><strong>Mercado Pago</strong> — Procesamiento de pagos (cuando aplique)</li>
                </ul>
                <p className="mt-2">Cada uno de estos proveedores cumple con sus propias políticas de privacidad y estándares de seguridad.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">6. Retención de datos</h2>
                <p>Conservamos tus datos mientras tu cuenta esté activa. Si eliminás tu cuenta:</p>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li>Datos de perfil: eliminados inmediatamente</li>
                  <li>Historial de precios y alertas: eliminados dentro de los 30 días</li>
                  <li>Datos de facturación: conservados por 10 años como exige la normativa tributaria</li>
                </ul>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">7. Tus derechos (Ley 25.326)</h2>
                <p>Tenés derecho a:</p>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li><strong>Acceso:</strong> solicitar información sobre los datos que tenemos sobre vos</li>
                  <li><strong>Rectificación:</strong> solicitar la corrección de datos incorrectos</li>
                  <li><strong>Eliminación:</strong> solicitar la eliminación de tu cuenta y datos personales</li>
                  <li><strong>Oposición:</strong> oponerte al tratamiento de tus datos para fines específicos</li>
                  <li><strong>Portabilidad:</strong> exportar tus datos en formato estructurado</li>
                </ul>
                <p className="mt-2">Para ejercer estos derechos, escribinos a <a href="mailto:howlify.app@gmail.com" className="text-red-400 hover:text-red-300 underline underline-offset-2">howlify.app@gmail.com</a>. Responderemos dentro de los 10 días hábiles.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">8. Cookies y tecnologías similares</h2>
                <p>Usamos cookies esenciales para el funcionamiento de la Plataforma (autenticación, preferencias de sesión). No usamos cookies de rastreo publicitario ni de terceros. Podés configurar tu navegador para rechazar cookies, aunque algunas funciones podrían no funcionar correctamente.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">9. Cambios en esta política</h2>
                <p>Nos reservamos el derecho de actualizar esta política de privacidad. Los cambios serán notificados por email y/o mediante un aviso en la Plataforma con al menos 30 días de anticipación.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">10. Autoridad de control</h2>
                <p>Si considerás que el tratamiento de tus datos no se ajusta a la normativa, podés presentar una consulta o reclamo ante la <strong>AAEP (Agencia de Acceso a la Información Pública)</strong> en <a href="https://www.argentina.gob.ar/aaep" target="_blank" rel="noopener noreferrer" className="text-red-400 hover:text-red-300 underline underline-offset-2">argentina.gob.ar/aaep</a>.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">11. Contacto</h2>
                <p>Titular: Alejandro Vázquez (CUIT 20-29479657-7)</p>
                <p>Email: <a href="mailto:howlify.app@gmail.com" className="text-red-400 hover:text-red-300 underline underline-offset-2">howlify.app@gmail.com</a></p>
              </section>
            </div>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
