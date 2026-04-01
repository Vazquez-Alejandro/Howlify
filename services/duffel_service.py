from duffel_api import Duffel
import os
from dotenv import load_dotenv

load_dotenv()

# Inicializamos el cliente oficial
DUFFEL_TOKEN = os.getenv("DUFFEL_ACCESS_TOKEN")
client = Duffel(access_token=DUFFEL_TOKEN)

def buscar_ofertas_vuelos(origen, destino, fecha):
    """
    Busca ofertas de vuelos ida y vuelta o solo ida.
    origin/destination: ej 'BUE', 'MAD'
    departure_date: 'YYYY-MM-DD'
    """
    try:
        # 1. Creamos el Offer Request
        slices = [
            {
                "origin": origen,
                "destination": destino,
                "departure_date": fecha,
            }
        ]
        passengers = [{"type": "adult"}]
        
        offer_request = client.offer_requests.create() \
            .slices(slices) \
            .passengers(passengers) \
            .execute()
        
        # 2. Retornamos la lista de ofertas
        return offer_request.offers
    except Exception as e:
        print(f"❌ Error Duffel: {e}")
        return None