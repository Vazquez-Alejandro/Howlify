import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def enviar_telegram(chat_id: str, oferta: dict, caza_nombre: str = "") -> bool:
    if not TELEGRAM_TOKEN or not chat_id:
        print("⚠ Telegram no configurado (Token o Chat ID ausente)")
        return False

    # Reutilizamos tu lógica de formateo (podés importar build_offer_message si querés)
    titulo = oferta.get("title") or "Oferta encontrada"
    precio = oferta.get("price") or "N/D"
    link = oferta.get("url") or ""
    
    # Formateo rápido estilo Lobo Ninja
    mensaje = (
        "🐺 *¡PRESA DETECTADA!* 🐺\n\n"
        f"🔎 *Caza:* {caza_nombre}\n"
        f"📦 *Producto:* {titulo}\n"
        f"💰 *Precio:* ${precio:,.0f}\n\n"
        f"🔗 [VER OFERTA]({link})"
    ).replace(",", ".") # Formato Arg

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "Markdown", # Para que las negritas y links queden pro
        "disable_web_page_preview": False
    }

    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.ok
    except Exception as e:
        print(f"❌ Error Telegram: {e}")
        return False