import os
from dotenv import load_dotenv
import requests

load_dotenv()

def test_envio():
    token = os.getenv("WHATSAPP_TOKEN")
    numero = "54111558210746" # Tu número de test
    url = "https://gate.whapi.cloud/messages/text"
    
    payload = {
        "to": f"{numero}@s.whatsapp.net",
        "body": "¡Lobo activado! 🐺 WhatsApp funcionando desde Whapi."
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    r = requests.post(url, json=payload, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")

if __name__ == "__main__":
    test_envio()