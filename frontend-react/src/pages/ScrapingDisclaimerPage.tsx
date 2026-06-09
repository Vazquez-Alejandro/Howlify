import { Link } from "react-router-dom";
import PageTransition from "../components/PageTransition";

export default function ScrapingDisclaimerPage() {
  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-950 px-4 py-12">
        <div className="max-w-2xl mx-auto">
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-red-400 transition-colors mb-8">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            Volver
          </Link>
          <div className="bg-gray-900/60 rounded-2xl p-8 md:p-10 border border-gray-800/50">
            <h1 className="text-2xl font-bold text-white mb-2">Aviso sobre obtención de datos</h1>
            <p className="text-sm text-gray-500 mb-6">Última actualización: junio 2026</p>

            <div className="space-y-6 text-sm text-gray-400 leading-relaxed">
              <section>
                <h2 className="text-base font-semibold text-white mb-2">Fuentes de información</h2>
                <p>Howlify obtiene información de precios de fuentes públicas disponibles en internet, incluyendo pero no limitándose a sitios de comercio electrónico, comparadores de precios y plataformas de viajes. Toda la información procesada es de acceso público y no requiere autenticación para su visualización.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">Naturaleza del servicio</h2>
                <p>Howlify es una herramienta de análisis y monitoreo de precios. Los datos mostrados son orientativos y tienen como finalidad ayudar al usuario a tomar decisiones informadas de compra. Howlify no es un vendedor, intermediario ni agente de ninguna tienda o plataforma de comercio electrónico.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">Exactitud de los datos</h2>
                <p>Los precios y disponibilidades mostrados pueden no estar actualizados en tiempo real. Howlify no garantiza la exactitud, completitud o vigencia de la información presentada. Los precios pueden variar sin previo aviso entre el momento de la consulta y el momento de la compra.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">Relación con terceros</h2>
                <p>Howlify no está afiliado, patrocinado ni avalado por MercadoLibre, Despegar, Airbnb ni ninguna otra plataforma cuyos precios sean monitoreados. Las marcas comerciales, logos y nombres comerciales pertenecen a sus respectivos titulares.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">Uso de la información</h2>
                <p>La información proporcionada por Howlify es para uso personal y no comercial del usuario. Queda prohibido redistribuir, revender o explotar comercialmente los datos obtenidos a través de la Plataforma sin autorización expresa del titular.</p>
              </section>

              <section>
                <h2 className="text-base font-semibold text-white mb-2">Contacto</h2>
                <p>Titular: Alejandro Vázquez (CUIT 20-29479657-7)</p>
                <p>Para consultas, escribinos a <a href="mailto:howlify.app@gmail.com" className="text-red-400 hover:text-red-300 underline underline-offset-2">howlify.app@gmail.com</a>.</p>
              </section>
            </div>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
