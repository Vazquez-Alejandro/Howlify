import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from auth.supabase_client import supabase  # Importamos tu cliente de Supabase

# Configuración de rutas y variables
current_dir = Path(__file__).resolve().parent
env_path = current_dir.parent / ".env"
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def enviar_mensaje(chat_id, texto):
    """Función auxiliar para enviar mensajes"""
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

                        # LÓGICA DE VINCULACIÓN AUTOMÁTICA
                        if texto_recibido.startswith("/start"):
                            partes = texto_recibido.split()
                            
                            # Si el comando tiene el ID (ej: /start UUID-DE-SUPABASE)
                            if len(partes) > 1:
                                supabase_user_id = partes[1]
                                try:
                                    # Actualizamos Supabase directamente
                                    supabase.table("users").update({
                                        "telegram_id": str(chat_id)
                                    }).eq("id", supabase_user_id).execute()
                                    
                                    respuesta = (
                                        f"¡Hola {user_name}! 🐺\n\n"
                                        "✅ **Cuenta vinculada con éxito.**\n"
                                        "Ya podés cerrar este chat. El Lobo te avisará por acá cuando bajen los precios."
                                    )
                                except Exception as e:
                                    print(f"❌ Error en Supabase: {e}")
                                    respuesta = "❌ Hubo un error al vincular tu cuenta. Reintentá desde la web."
                            else:
                                # Si entra sin link (manual)
                                respuesta = (
                                    f"¡Hola {user_name}! 🐺\n\n"
                                    f"Tu ID es: `{chat_id}`\n"
                                    "Para vincularte automáticamente, usá el botón 'Vincular' en la web de Howlify."
                                )
                            
                            enviar_mensaje(chat_id, respuesta)

        except Exception as e:
            print(f"❌ Error en el bucle: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    main()