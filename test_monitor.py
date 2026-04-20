import os, time, random
from playwright.sync_api import sync_playwright
from supabase import create_client, Client

# Conexión a Supabase
url = "https://aqzkysgzljxqmckzfpfq.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxemt5c2d6bGp4cW1ja3pmcGZxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIxMTU4NTMsImV4cCI6MjA4NzY5MTg1M30.XDqg5IG1ES_4UWAuWxwdGws43siLhYkDZciIRVzr3Lc"
supabase: Client = create_client(url, key)

# Usamos un caza_id real
caza_id = 129
url_test = "https://example.com"
ruta = f"evidence/evidencia_{caza_id}.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    try:
        page.goto(url_test, timeout=60000, wait_until="domcontentloaded")
        time.sleep(random.uniform(2, 4))
        os.makedirs("evidence", exist_ok=True)
        page.screenshot(path=ruta, full_page=True)
        size = os.path.getsize(ruta)

        print(f"📸 Captura guardada: {ruta} ({size} bytes)")

        supabase.table("infracciones_log").insert({
            "caza_id": caza_id,
            "url_captura": ruta,
            "precio_detectado": 0
        }).execute()
        print("✅ Registro insertado en Supabase con caza_id=129")

    except Exception as e:
        print("❌ Error en prueba:", e)
    finally:
        browser.close()
