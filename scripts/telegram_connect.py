import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv


current_dir = Path(__file__).resolve().parent
env_path = current_dir.parent / ".env"
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def main():
    if not TOKEN:
        print("❌ ERROR: No encontré el TELEGRAM_TOKEN en el .env")
        return

    print("🐺 Lobo a la escucha en Telegram... (Ctrl+C para salir)")
    offset = None
    
    while True:
        try:
            # Consultamos mensajes nuevos (Polling)
            url = f"{API_URL}/getUpdates"
            params = {"timeout": 20, "offset": offset}
            res = requests.get(url, params=params).json()

            if "result" in res:
                for update in res["result"]:
                    # Marcamos como leído
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    
                    if msg and "text" in msg:
                        chat_id = msg["chat"]["id"]
                        user_name = msg["from"].get("first_name", "Cazador")
                        
                        print(f"📩 Mensaje de {user_name} (ID: {chat_id})")

                        # Respondemos con el ID para que el usuario lo copie
                        texto = (
                            f"¡Hola {user_name}! 🐺\n\n"
                            f"Tu **ID de Rastreo** es:\n`{chat_id}`\n\n"
                            "Copiá ese número y pegalo en la configuración de Howlify para activar tus alertas."
                        )
                        requests.post(f"{API_URL}/sendMessage", json={
                            "chat_id": chat_id, 
                            "text": texto, 
                            "parse_mode": "Markdown"
                        })
        except Exception as e:
            print(f"❌ Error en el Listener: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    main()