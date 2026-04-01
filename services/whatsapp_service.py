import os
from pathlib import Path

import requests
from dotenv import load_dotenv

CURRENT_FILE = Path(__file__).resolve()
ROOT_ENV = CURRENT_FILE.parents[2] / ".env"
PACKAGE_ENV = CURRENT_FILE.parents[1] / ".env"

if ROOT_ENV.exists():
    load_dotenv(ROOT_ENV)
elif PACKAGE_ENV.exists():
    load_dotenv(PACKAGE_ENV)
else:
    load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").strip()
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()

# Si existe, en sandbox se usa SIEMPRE este número
TEST_WHATSAPP_TO = os.getenv("TEST_WHATSAPP_TO", "").strip()


def _format_price(precio) -> str:
    try:
        return f"${int(float(precio)):,}".replace(",", ".")
    except Exception:
        return str(precio)


def _infer_source_label(oferta: dict) -> str:
    source = (oferta.get("source") or "").strip().lower()
    if source == "mercadolibre":
        return "MercadoLibre"
    if source == "fravega":
        return "Frávega"
    if source == "despegar":
        return "Despegar"
    if source == "tripstore":
        return "Tripstore"
    if source == "generic":
        return "Tienda"
    return source.capitalize() if source else "Tienda"


def build_offer_message(oferta: dict, caza_nombre: str = "") -> str:
    titulo = oferta.get("title") or oferta.get("titulo") or "Oferta encontrada"
    precio = oferta.get("price") or oferta.get("precio") or "N/D"
    link = oferta.get("url") or oferta.get("link") or ""
    source_label = _infer_source_label(oferta)
    precio_txt = _format_price(precio)

    caza_line = f"🔎 Caza: {caza_nombre}\n" if caza_nombre else ""

    return (
        "🐺 Howlify detectó una oferta\n\n"
        f"{caza_line}"
        f"📦 Producto: {titulo}\n"
        f"💰 Precio: {precio_txt}\n"
        f"🏪 Fuente: {source_label}\n\n"
        f"🔗 {link}"
    )


def enviar_whatsapp(numero: str, oferta: dict, caza_nombre: str = "") -> bool:
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        print("⚠ WhatsApp no configurado (faltan variables de entorno)")
        return False

    destino = TEST_WHATSAPP_TO if TEST_WHATSAPP_TO else (numero or "").strip()

    if not destino:
        print("⚠ No hay número de destino para WhatsApp")
        return False

    mensaje = build_offer_message(oferta, caza_nombre=caza_nombre)

    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": destino,
        "type": "text",
        "text": {"body": mensaje},
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)

        if not r.ok:
            print(f"⚠ Error WhatsApp {r.status_code}: {r.text}")
            return False

        print(f"📲 WhatsApp enviado a {destino}")
        return True

    except Exception as e:
        print("⚠ Error enviando WhatsApp:", e)
        return False