import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from utils.logger import get_logger
logger = get_logger("tg")


# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

try:
    from auth.supabase_client import supabase
except ImportError:
    logger.error("❌ ERROR: No se pudo importar supabase_client. Revisá la estructura de carpetas.")

# Carga de entorno
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def enviar_mensaje(chat_id, texto):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")

def main():
    if not TOKEN:
        logger.error("❌ ERROR: No se encontró TELEGRAM_TOKEN")
        return

    logger.info("🐺 Lobo a la escucha en Telegram (Modo Auto-Vinculación)...")
    offset = None
    
    while True:
        try:
            url = f"{API_URL}/getUpdates"
            params = {"timeout": 20, "offset": offset}
            res = requests.get(url, params=params, timeout=25).json()

            if "result" in res:
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    
                    if msg and "text" in msg:
                        chat_id = msg["chat"]["id"]
                        texto_recibido = msg["text"]
                        user_name = msg["from"].get("first_name", "Cazador")

                        if texto_recibido.startswith("/start"):
                            partes = texto_recibido.split()
                            
                            if len(partes) > 1:
                                bind_token = partes[1].strip()
                                logger.info(f"🔍 Intentando vincular chat_id {chat_id} con token {bind_token[:8]}...")
                                
                                try:
                                    # Verify token against stored telegram_bind_token
                                    profile = supabase.table("profiles").select("user_id, telegram_bind_token").eq("telegram_bind_token", bind_token).limit(1).execute()
                                    
                                    if profile.data and len(profile.data) > 0:
                                        user_id = profile.data[0]["user_id"]
                                        resultado = supabase.table("profiles").update({
                                            "telegram_id": str(chat_id),
                                            "telegram_bind_token": None,
                                        }).eq("user_id", user_id).execute()
                                        
                                        logger.info(f"✅ Éxito: Perfil actualizado para {user_id}")
                                        respuesta = f"¡Hola {user_name}! 🐺\n\n✅ **Cuenta vinculada con éxito.**"
                                    else:
                                        logger.warning(f"⚠️ Token inválido: {bind_token[:8]}...")
                                        respuesta = "❌ Token inválido o expirado. Generá uno nuevo desde la web."
                                        
                                except Exception as e:
                                    logger.error(f"❌ Error en Supabase: {e}")
                                    respuesta = "❌ Error técnico al guardar en la base de datos."
                            else:
                                respuesta = f"¡Hola {user_name}! 🐺\nUsá el link de la web para vincular tu cuenta."
                            
                            enviar_mensaje(chat_id, respuesta)

        except Exception as e:
            logger.error(f"❌ Error en el bucle: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    main()