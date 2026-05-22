import os
import requests
from dotenv import load_dotenv

load_dotenv()

DUFFEL_TOKEN = os.getenv("DUFFEL_ACCESS_TOKEN")

def buscar_ofertas_vuelos(origen, destino, fecha):
    """
    Consulta directa usando la versión v2 que ya sabemos que funciona.
    """
    if not DUFFEL_TOKEN:
        print("❌ Error: No se encontró DUFFEL_ACCESS_TOKEN")
        return None

    url = "https://api.duffel.com/air/offer_requests"
    
    # Forzamos la v2 que me confirmaste
    headers = {
        "Authorization": f"Bearer {DUFFEL_TOKEN}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json"
    }

    # Limpiamos los códigos IATA
    ori = origen.strip().upper()[:3]
    des = destino.strip().upper()[:3]

    # Estructura de datos para la v2
    payload = {
        "data": {
            "slices": [
                {
                    "origin": ori,
                    "destination": des,
                    "departure_date": fecha
                }
            ],
            "passengers": [{"type": "adult"}],
            "cabin_class": "economy"
        }
    }

    try:
        print(f"🚀 [API-v2] Consultando: {ori} -> {des} para el {fecha}...")
        
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code != 201:
            # Si vuelve a fallar, este print nos va a decir exactamente POR QUÉ
            print(f"❌ Error API Duffel v2 ({response.status_code}): {response.text}")
            return []

        data = response.json()
        offers = data.get("data", {}).get("offers", [])
        
        # Clase auxiliar para que el Engine no se rompa
        class SimpleOffer:
            def __init__(self, raw_offer):
                self.total_amount = float(raw_offer.get("total_amount", 0))
                self.destination = type('obj', (object,), {'name': des})

        print(f"✅ [Duffel v2] ¡ÉXITO! Se encontraron {len(offers)} ofertas.")
        return [SimpleOffer(o) for o in offers]

    except Exception as e:
        print(f"❌ Error en la conexión v2: {e}")
        return []