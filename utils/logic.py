import random
import time

# ==========================================================
# 1. ESTRATEGIA DE PRECIOS (Lo que ya tenías, mejorado)
# ==========================================================
def evaluar_oferta(precio_actual, config):
    """Determina si el precio encontrado es una 'presa' digna del Lobo."""
    tipo = config.get('tipo')
    objetivo = config.get('objetivo')

    if tipo == 'piso':
        if precio_actual <= objetivo:
            return True, f"¡Bajó del piso de ${objetivo:,}!".replace(",", ".")
            
    elif tipo == 'descuento':
        ref = config.get('precio_referencia')
        if not ref: return False, ""
        ahorro = ((ref - precio_actual) / ref) * 100
        if ahorro >= objetivo:
            return True, f"¡Superó el {objetivo}% de descuento! (Ahorro real: {int(ahorro)}%)"

    return False, ""

# ==========================================================
# 2. ESTRATEGIA NINJA (Anti-Bloqueo para el Punto 5)
# ==========================================================
def get_random_user_agent():
    """Devuelve un disfraz distinto para que ML no nos huela."""
    disfraces = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.105 Mobile Safari/537.36"
    ]
    return random.choice(disfraces)

def apply_human_jitter():
    """Pausa aleatoria para que el Lobo no parezca un script de 2 pesos."""
    # Entre 1.5 y 4 segundos de 'pensamiento'
    delay = random.uniform(1.5, 4.0)
    time.sleep(delay)
    return delay