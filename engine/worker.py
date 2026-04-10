import time
import signal
import sys
import os # <--- Agregamos este
from datetime import datetime, timedelta, timezone

# --- 🐺 EL "FIX" DE RUTAS PARA LINUX ---
# Esto le dice a Python que suba un nivel ('..') para encontrar las otras carpetas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ahora los imports van a funcionar perfecto
from auth.supabase_client import supabase  
from scraper.scraper_pro import hunt_offers 
# ---------------------------------------

def obtener_cazas_pendientes():
    """
    Busca cacerías sincronizadas por bloques de tiempo (00, 15, 30, 45).
    """
    ahora = datetime.now(timezone.utc)
    minuto_actual = ahora.minute
    
    query = supabase.table("cazas").select("*").eq("estado", "activa").execute()
    pendientes = []

    for caza in query.data:
        last_check = caza.get("last_check")
        
        # Extraemos el número de la frecuencia (ej: "15 min" -> 15)
        try:
            frecuencia_min = int(caza["frecuencia"].split()[0])
        except:
            frecuencia_min = 15 # Default por seguridad

        # --- 🐺 LÓGICA DE SINCRONIZACIÓN ---
        # Verificamos si el minuto actual es múltiplo de la frecuencia
        # Ej: Si frecuencia es 15, dispara en :00, :15, :30, :45
        es_momento_de_bloque = (minuto_actual % frecuencia_min == 0)

        if es_momento_de_bloque:
            # Si nunca se chequeó, entra de una al bloque
            if not last_check:
                pendientes.append(caza)
                continue
            
            # Si ya se chequeó, verificamos que no haya sido en este MISMO bloque
            # (para evitar que el worker dispare 60 veces durante el mismo minuto)
            last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
            diferencia = ahora - last_check_dt
            
            if diferencia > timedelta(seconds=70): 
                pendientes.append(caza)

    return pendientes

def main():
    print("🐺 LOBO GUARDIÁN: Iniciando sistema de vigilancia pro...")
    
    while True:
        try:
            print(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] Escaneando agenda en Supabase...")
            cazas = obtener_cazas_pendientes()
            
            if cazas:
                print(f"🎯 Encontradas {len(cazas)} cacerías vencidas. Lanzando jauría...")
                for caza in cazas:
                    print(f"🔎 Procesando: {caza['producto']} (ID: {caza['id']})")
                    
                    # Guardamos el precio histórico antes de la nueva búsqueda
                    precio_anterior = caza.get("ultimo_precio_detectado") 
                    precio_objetivo = caza.get("precio_max")
                    
                    # 🔥 LANZAMOS AL LOBO
                    resultados = hunt_offers(
                        url=caza.get("link"),
                        keyword=caza.get("producto"),
                        max_price=caza.get("precio_max"),
                        es_pro=(caza.get("plan") in ["pro", "business"]),
                        headless=True,
                        user_id=caza.get("user_id"),
                        caza_id=caza.get("id"),
                        plan=caza.get("plan", "starter")
                    )

                    # Preparar la actualización de la base de datos
                    update_data = {
                        "last_check": datetime.now(timezone.utc).isoformat()
                    }

                    if resultados:
                        precio_actual = resultados[0].get("price")
                        print(f"✅ Presas detectadas ({len(resultados)}) para '{caza['producto']}'. Precio: ${precio_actual}")
                        
                        # --- 🐺 DETECCIÓN PARA EL SEMÁFORO ---
                        
                        # 🟢 Caso 1: ¡Llegamos al objetivo!
                        if precio_actual <= precio_objetivo:
                            print(f"🎯 ¡OBJETIVO ALCANZADO! {caza['producto']} bajó a ${precio_actual} (VERDE 🟢)")
                        
                        # 🔴 Caso 2: El precio SUBIÓ (Inflación)
                        elif precio_anterior and precio_actual > precio_anterior:
                            diferencia = precio_actual - precio_anterior
                            porcentaje = (diferencia / precio_anterior) * 100
                            print(f"⚠️ AVISO DE AUMENTO: {caza['producto']} subió +${diferencia} ({porcentaje:.1f}%) (ROJO 🔴)")
                        
                        # 🟡 Caso 3: El precio BAJÓ pero no al objetivo todavía
                        elif precio_anterior and precio_actual < precio_anterior:
                            diferencia = precio_anterior - precio_actual
                            print(f"📉 REBAJA DETECTADA: {caza['producto']} bajó -${diferencia} (AMARILLO 🟡)")

                        # Guardamos el nuevo precio detectado para la próxima comparación
                        update_data["ultimo_precio_detectado"] = precio_actual
                    else:
                        print(f"💨 Sin novedades para '{caza['producto']}'.")

                    # Actualizamos Supabase para que el reloj de frecuencia vuelva a contar
                    supabase.table("cazas").update(update_data).eq("id", caza["id"]).execute()  
                    
            else:
                print("💤 Nada que cazar por ahora. Todo bajo control.")

        except Exception as e:
            print(f"❌ Error crítico en el ciclo del Worker: {e}")

        # Chequeamos cada 60 segundos el reloj de Supabase
        time.sleep(60)

def _handle_exit(signum, frame):
    print(f"\n🛑 Apagando el Lobo Guardián de forma segura... [Signal {signum}]")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)
    main()