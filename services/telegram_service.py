import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def enviar_telegram(chat_id, mensaje, parse_mode="Markdown"):
    # 🐺 IMPORTANTE: Usá el nombre EXACTO que tenés en el .env
    # En tu .env pusiste TELEGRAM_TOKEN, así que acá va ese.
    token = os.getenv("TELEGRAM_TOKEN") 
    
    if not token or not chat_id:
        # Este print saldrá en tu terminal de Linux Mint si algo falla
        print(f"⚠ Telegram Error. Token: {'OK' if token else 'FALTA'}, Chat ID: {chat_id}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error conexión: {e}")
        return False
    
def enviar_alerta_oferta(chat_id, oferta, caza_nombre=""):
    """Específico para productos (tu lógica original mejorada)"""
    titulo = oferta.get("title") or "Oferta encontrada"
    link = oferta.get("url") or ""
    
    # Manejo robusto del precio para que no rompa si no es número
    try:
        precio_raw = oferta.get("price", 0)
        precio_formateado = f"${float(precio_raw):,.0f}".replace(",", ".")
    except:
        precio_formateado = f"${oferta.get('price', 'N/D')}"

    mensaje = (
        "🐺 *¡PRESA DETECTADA!* 🐺\n\n"
        f"🔎 *Caza:* {caza_nombre}\n"
        f"📦 *Producto:* {titulo}\n"
        f"💰 *Precio:* {precio_formateado}\n\n"
        f"🔗 [VER OFERTA]({link})"
    )
    return enviar_telegram(chat_id, mensaje)

def enviar_alerta_vuelo(chat_id, vuelo_data):
    """Específico para los vuelos de Duffel que vamos a cazar"""
    # Esta la usaremos cuando integremos el worker de Duffel
    mensaje = (
        "✈️ *¡VUELO CAZADO POR EL LOBO!* ✈️\n\n"
        f"🌍 *Ruta:* {vuelo_data['origen']} -> {vuelo_data['destino']}\n"
        f"💸 *Precio:* {vuelo_data['moneda']} {vuelo_data['precio']}\n"
        f"📅 *Fecha:* {vuelo_data['fecha']}\n\n"
        "🔗 [RESERVAR AHORA](https://duffel.com)"
    )
    return enviar_telegram(chat_id, mensaje)