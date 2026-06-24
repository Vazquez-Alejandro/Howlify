import os
import sys
import time
import random
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auth.supabase_client import supabase
from utils.logic import get_random_user_agent, apply_human_jitter
from utils.logger import get_logger
logger = get_logger("ml_monitor")

def ejecutar_monitor():
    logger.info("🐺 [DEBUG] LOBO INICIADO")
    try:
        res = supabase.table("monitor_rules").select("*").execute()
        reglas = res.data

        if not reglas:
            logger.info("🌕 Radar vacío.")
            return

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

            for regla in reglas:
                caza_id = regla.get("caza_id")
                url = regla.get("product_url")

                logger.info(f"🎯 Procesando Caza ID: {caza_id}...")

                # Validar que el caza_id exista en cazas
                exists = supabase.table("cazas").select("id").eq("id", caza_id).execute()
                if not exists.data:
                    supabase.table("cazas").insert({
                        "id": caza_id,
                        "producto": regla.get("producto") or "SIN NOMBRE",
                        "user_id": regla.get("user_id"),
                        "link": url
                    }).execute()
                    logger.info(f"📝 Insertado nuevo registro en cazas con ID {caza_id}")

                context = browser.new_context(user_agent=get_random_user_agent())
                page = context.new_page()

                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    time.sleep(random.uniform(3, 5))

                    # 📊 Scraping del título del producto
                    try:
                        titulo = page.query_selector("h1.ui-pdp-title").inner_text()
                        if titulo:
                            supabase.table("cazas").update({"producto": titulo}).eq("id", caza_id).execute()
                    except Exception as e_titulo:
                        logger.warning(f"⚠️ No se pudo extraer título: {e_titulo}")

                    # 📊 Scraping del precio actual
                    precio_real = 0
                    try:
                        precio_text = page.query_selector("span.andes-money-amount__fraction").inner_text()
                        precio_real = int(precio_text.replace(".", "").replace(",", "").strip())
                        logger.info(f"💰 Precio detectado: {precio_real}")
                    except Exception as e_precio:
                        logger.warning(f"⚠️ No se pudo extraer precio: {e_precio}")

                    # Guardar historial de precios
                    if precio_real > 0:
                        supabase.table("price_history").insert({
                            "caza_id": caza_id,
                            "user_id": regla.get("user_id"),  # incluir user_id si la tabla lo requiere
                            "price": precio_real,
                            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")
                        }).execute()
                        logger.info(f"📈 price_history actualizado para ID {caza_id}")

                    # Captura de pantalla
                    os.makedirs("evidence", exist_ok=True)
                    ruta = f"evidence/evidencia_{caza_id}.png"
                    page.screenshot(path=ruta, full_page=True)

                    size = os.path.getsize(ruta)
                    if size < 2000:
                        logger.warning(f"⚠️ Captura sospechosa ({size} bytes). Puede ser login/captcha.")
                        status = "screenshot_failed"
                        ruta_final = None
                        error_msg = "Captura sospechosa (archivo muy pequeño)"
                    else:
                        logger.info(f"📸 Captura guardada: {ruta} ({size} bytes)")
                        status = "detected"
                        ruta_final = ruta
                        error_msg = None

                    # Guardar evidencia en infracciones_log
                    supabase.table("infracciones_log").insert({
                        "caza_id": caza_id,
                        "url_captura": ruta_final,
                        "precio_detectado": precio_real,
                        "status": status,
                        "error": error_msg
                    }).execute()
                    logger.info(f"✅ DB Actualizada para ID: {caza_id} con estado {status}")

                except Exception as e_page:
                    logger.error(f"❌ Error en página {caza_id}: {e_page}")
                    supabase.table("infracciones_log").insert({
                        "caza_id": caza_id,
                        "url_captura": None,
                        "precio_detectado": 0,
                        "status": "error",
                        "error": str(e_page)
                    }).execute()

                finally:
                    page.close()

            browser.close()

    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    ejecutar_monitor()
