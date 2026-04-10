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
    MODO TEST: Consulta Supabase buscando SOLO la cacería 92
    """
    ahora = datetime.now(timezone.utc)
    
    # En engine/worker.py, dentro de obtener_cazas_pendientes:
    query = supabase.table("cazas").select("*").eq("estado", "activa").execute()
    # --------------------------------------------
    
    pendientes = []
    for caza in query.data:
        last_check = caza.get("last_check")
        
        if not last_check:
            pendientes.append(caza)
            continue
            
        try:
            minutos_val = int(caza["frecuencia"].split()[0])
        except:
            minutos_val = 60
            
        # Convertimos last_check a objeto consciente de UTC
        last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
        proximo_chequeo = last_check_dt + timedelta(minutes=minutos_val)
        
        # 🐺 Solo si pasó el tiempo, lo agregamos a la jauría
        if ahora >= proximo_chequeo:
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
                        
                        # 📈 Lógica de Aviso de Aumento (Solo Pro y Business)
                        if precio_anterior and precio_actual > precio_anterior:
                            if caza.get("plan") in ["pro", "business"]:
                                print(f"⚠️ AVISO DE AUMENTO: {caza['producto']} subió de ${precio_anterior} a ${precio_actual}")
                                # Aquí es donde el Telegram dirá: "Che, esto subió"
                        
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