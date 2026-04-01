import requests
import streamlit as st

def get_dolar_tarjeta():
    """Trae la cotización del Dólar Tarjeta/Turista (Oficial + Impuestos)"""
    try:
        # Usamos DolarApi que es rápida y sin tokens
        response = requests.get("https://dolarapi.com/v1/dolares/tarjeta", timeout=5)
        data = response.json()
        return float(data['venta'])
    except Exception as e:
        print(f"❌ Error al traer cotización: {e}")
        return 1600.0  # Un "fallback" seguro por si la API cae