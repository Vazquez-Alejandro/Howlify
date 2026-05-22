import { Link } from "react-router-dom";
import PageTransition from "../components/PageTransition";

export default function PrivacyPage() {
  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-950 px-4 py-12">
        <div className="max-w-2xl mx-auto">
          <Link to="/register" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-red-400 transition-colors mb-8">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            Volver
          </Link>
          <div className="bg-gray-900/60 rounded-2xl p-8 md:p-10 border border-gray-800/50">
            <h1 className="text-2xl font-bold text-white mb-6">Política de Privacidad</h1>
            <p className="text-sm text-gray-500 mb-6">Última actualización: mayo 2026</p>

            <div className="space-y-6 text-sm text-gray-400 leading-relaxed">
              <section>
                <h2 className="text-base font-semibold text-white mb-2">1. Datos que recopilamos</h2>
                <p>Recopilamos la siguiente información cuando creás una cuenta:</p>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li>Dirección de email</li>
                  <li>Nombre de usuario</li>
                  <li>Plan de suscripción seleccionado</li>
                  <li>Preferencias de notificación (WhatsApp, Telegram, email)</li>
                </ul>
                <p className="mt-2">También almacenamos las URLs de productos que monitoreás y el historial de precios asociado.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">2. Cómo usamos tus datos</h2>
                <p>Usamos tus datos para:</p>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li>Proveer y mantener el servicio de monitoreo</li>
                  <li>Enviar alertas de precios según tus preferencias</li>
                  <li>Generar reportes y análisis de precios</li>
                  <li>Mejorar la Plataforma y diagnosticar problemas</li>
                  <li>Comunicarnos sobre cambios en el servicio o facturación</li>
                </ul>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">3. Almacenamiento y seguridad</h2>
                <p>Tus datos se almacenan en servidores seguros de Supabase (PostgreSQL) con cifrado en tránsito y en reposo. Implementamos medidas de seguridad estándar para proteger tu información contra accesos no autorizados.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">4. Compartición de datos</h2>
                <p>No vendemos ni compartimos tus datos personales con terceros. Podemos compartir datos anonimizados y agregados para fines estadísticos. Usamos servicios de terceros (Supabase, Resend, Stripe) que cumplen con sus propias políticas de privacidad y estándares de seguridad.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">5. Retención de datos</h2>
                <p>Conservamos tus datos mientras tu cuenta esté activa. Si eliminás tu cuenta, los datos asociados se eliminan en un plazo de 30 días. El historial de precios puede conservarse anonimizado para fines estadísticos.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">6. Tus derechos</h2>
                <p>Tenés derecho a:</p>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li>Acceder a tus datos personales</li>
                  <li>Solicitar la corrección de datos incorrectos</li>
                  <li>Solicitar la eliminación de tu cuenta y datos</li>
                  <li>Exportar tus datos en formato estructurado</li>
                  <li>Revocar el consentimiento para notificaciones</li>
                </ul>
                <p className="mt-2">Para ejercer estos derechos, contactanos a <a href="mailto:soporte@howlify.app" className="text-red-400 hover:text-red-300 underline underline-offset-2">soporte@howlify.app</a>.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">7. Cookies</h2>
                <p>Usamos cookies esenciales para el funcionamiento de la Plataforma (autenticación, sesión). No usamos cookies de rastreo publicitario. Podés configurar tu navegador para rechazar cookies, aunque algunas funciones podrían no funcionar correctamente.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">8. Cambios en esta política</h2>
                <p>Nos reservamos el derecho de actualizar esta política de privacidad. Los cambios serán notificados por email y/o mediante un aviso en la Plataforma.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">9. Contacto</h2>
                <p>Si tenés preguntas sobre esta política de privacidad, escribinos a <a href="mailto:soporte@howlify.app" className="text-red-400 hover:text-red-300 underline underline-offset-2">soporte@howlify.app</a>.</p>
              </section>
            </div>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
