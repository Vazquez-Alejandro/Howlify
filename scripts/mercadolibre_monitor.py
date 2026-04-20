import os
import sys
import time
import random
from supabase import create_client
# Importamos las herramientas ninja que arreglamos ayer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logic import get_random_user_agent, apply_human_jitter

# CONFIGURACIÓN
URL = "https://aqzkysgzljxqmckzfpfq.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxemt5c2d6bGp4cW1ja3pmcGZxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIxMTU4NTMsImV4cCI6MjA4NzY5MTg1M30.XDqg5IG1ES_4UWAuWxwdGws43siLhYkDZciIRVzr3Lc"
supabase = create_client(URL, KEY)

def ejecutar_monitor():
    print("🐺 [DEBUG] LOBO INICIADO")
    try:
        res = supabase.table("monitor_rules").select("*").execute()
        reglas = res.data
        
        if not reglas:
            print("🌕 Radar vacío.")
            return

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Lanzamos el navegador una sola vez para todas las capturas
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            
            for regla in reglas:
                caza_id = regla.get("caza_id")
                url = regla.get("product_url")
                
                print(f"🎯 Procesando Caza ID: {caza_id}...")
                
                # Contexto con User Agent aleatorio para no ser bloqueado
                context = browser.new_context(user_agent=get_random_user_agent())
                page = context.new_page()
                
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    time.sleep(random.uniform(3, 5)) # Delay humano para que cargue ML
                    
                    os.makedirs("evidence", exist_ok=True)
                    ruta = f"evidence/evidencia_{caza_id}.png"
                    page.screenshot(path=ruta, full_page=False)
                    print(f"📸 Captura guardada: {ruta}")
                    
                    # REGISTRO EN DB
                    data_log = {
                        "caza_id": caza_id,
                        "url_captura": ruta,
                        "precio_detectado": 0 # Aquí irá el scraping después
                    }
                    
                    # Intentamos insertar. Si falla por el ID, lo atrapamos.
                    try:
                        supabase.table("infracciones_log").insert(data_log).execute()
                        print(f"✅ DB Actualizada para ID: {caza_id}")
                    except Exception as e_db:
                        print(f"⚠️ Error de ID: Asegurate que el ID {caza_id} exista en la tabla 'cazas'.")

                except Exception as e_page:
                    print(f"❌ Error en página {caza_id}: {e_page}")
                
                page.close()
            browser.close()

    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    ejecutar_monitor()