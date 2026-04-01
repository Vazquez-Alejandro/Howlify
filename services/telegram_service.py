import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def enviar_telegram(chat_id, mensaje, parse_mode="Markdown"):
    """Función base para enviar CUALQUIER cosa por Telegram"""
    if not TELEGRAM_TOKEN or not chat_id:
        print("⚠ Telegram no configurado (Token o Chat ID ausente)")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False
    }

    try:
        r = requests.post(url, json=payload, timeout=15)
        if not r.ok:
            print(f"❌ Error API Telegram: {r.text}")
        return r.ok
    except Exception as e:
        print(f"❌ Error de conexión Telegram: {e}")
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