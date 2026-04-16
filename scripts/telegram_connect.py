import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# --- ARREGLO DE RUTAS PARA RENDER ---
# Esto hace que el script vea la carpeta 'auth' y 'services' desde la raíz
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from auth.supabase_client import supabase  # Ahora sí lo va a encontrar

# Carga de entorno
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def enviar_mensaje(chat_id, texto):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")

def main():
    if not TOKEN:
        print("❌ ERROR: No se encontró TELEGRAM_TOKEN")
        return

    print("🐺 Lobo a la escucha en Telegram (Modo Auto-Vinculación)...")
    offset = None
    
    while True:
        try:
            url = f"{API_URL}/getUpdates"
            params = {"timeout": 20, "offset": offset}
            res = requests.get(url, params=params).json()

            if "result" in res:
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    
                    if msg and "text" in msg:
                        chat_id = msg["chat"]["id"]
                        texto_recibido = msg["text"]
                        user_name = msg["from"].get("first_name", "Cazador")

                        print(f"📩 Procesando mensaje de {user_name}...")

                        if texto_recibido.startswith("/start"):
                            partes = texto_recibido.split()
                            
                            if len(partes) > 1:
                                supabase_user_id = partes[1]
                                try:
                                    # Actualizamos la tabla 'profiles' (que es la que mostraste en la captura)
                                    supabase.table("profiles").update({
                                        "telegram_id": str(chat_id)
                                    }).eq("user_id", supabase_user_id).execute()
                                    
                                    respuesta = f"¡Hola {user_name}! 🐺\n\n✅ **Cuenta vinculada con éxito.**"
                                except Exception as e:
                                    print(f"❌ Error en Supabase: {e}")
                                    respuesta = "❌ Hubo un error al vincular tu cuenta."
                            else:
                                respuesta = f"¡Hola {user_name}! 🐺\nUsa el link de la web para vincularte."
                            
                            enviar_mensaje(chat_id, respuesta)

        except Exception as e:
            print(f"❌ Error en el bucle: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    main()