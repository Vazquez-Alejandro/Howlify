import os
from duffel_service import buscar_vuelos_simples # Importamos tu servicio de Duffel

def hunt_vuelos(origen, destino, config_usuario):
    # origen y destino pueden ser nombres o IATA (ej: 'BUE', 'MAD')
    # Duffel prefiere IATA, si mandás "Madrid" hay que convertirlo o mandarlo directo
    
    print(f"\n🚀 [Duffel] Rastreando: {origen} -> {destino}")
    
    try:
        # 1. LLAMADA A LA API (Sin navegadores, sin captchas)
        vuelos = buscar_vuelos_simples(dest=destino) 
        
        if not vuelos:
            print("🚨 Duffel no encontró vuelos para esa ruta en estas fechas.")
            return

        # 2. PROCESAMIENTO DE PRECIOS
        # Duffel suele devolver en USD o moneda local. 
        # Asegurate de que 'config_usuario' y Duffel hablen la misma moneda.
        precios_encontrados = [v['price'] for v in vuelos]
        menor_precio = min(precios_encontrados)
        print(f"✅ Menor precio detectado vía API: ${menor_precio}")

        # 3. LÓGICA DE ALERTA (Mantenemos tu lógica que estaba perfecta)
        tipo = config_usuario.get('tipo') 
        objetivo = config_usuario.get('objetivo')
        disparar = False
        msg = ""

        if tipo == 'piso':
            if menor_precio <= objetivo:
                disparar = True
                msg = f"🔥 ¡Bajó del piso! Precio actual: ${menor_precio} (Límite: ${objetivo})"
        
        elif tipo == 'descuento':
            ref = config_usuario.get('precio_referencia', 0)
            if ref > 0:
                ahorro = ((ref - menor_precio) / ref) * 100
                if ahorro >= objetivo:
                    disparar = True
                    msg = f"📉 ¡OFERTÓN! Descuento del {int(ahorro)}% (Buscabas {objetivo}%)"

        if disparar:
            print(f"\n📢 DISPARANDO NOTIFICACIÓN: {msg}")
            # Acá llamamos a tu función de Telegram
            # send_telegram_msg(msg) 
        else:
            print("😴 No hay ofertas que cumplan el criterio de Duffel todavía.")

    except Exception as e:
        print(f"❌ Error en la cacería con Duffel: {e}")