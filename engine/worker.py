import time
import signal
import sys
import os 
from datetime import datetime, timedelta, timezone

# --- 🐺 EL "FIX" DE RUTAS PARA LINUX ---
# Esto le dice a Python que suba un nivel ('..') para encontrar las otras carpetas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ahora los imports van a funcionar perfecto
from auth.supabase_client import supabase  
from scraper.scraper_pro import hunt_offers 
from services.notification_service import despachar_alertas_jauria


# ---------------------------------------

def obtener_cazas_pendientes():
    """
    Busca cacerías sincronizadas por bloques de tiempo (00, 15, 30, 45).
    """
    ahora = datetime.now(timezone.utc)
    minuto_actual = ahora.minute
    
    query = supabase.table("cazas").select("*, profiles(email, telegram_id, plan, whatsapp_number)").eq("estado", "activa").execute()
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
                    
                    precio_anterior = caza.get("ultimo_precio_detectado") 
                    precio_objetivo = caza.get("precio_max")
                    last_alert_str = caza.get("last_alert_at")
                    
                    # 🔥 LANZAMOS AL LOBO (Scraper)
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

                    update_data = {
                        "last_check": datetime.now(timezone.utc).isoformat()
                    }

                    if resultados:
                        precio_actual = resultados[0].get("price")
                        print(f"✅ Presa detectada para '{caza['producto']}'. Precio actual: ${precio_actual}")
                        
                        # --- 🐺 LÓGICA DE SEMÁFORO INTELIGENTE ---
                        estado = "🟢" 
                        variacion = 0
                        if precio_anterior:
                            variacion = ((precio_actual - precio_anterior) / precio_anterior) * 100

                        if precio_actual <= precio_objetivo:
                            estado = "🔴" 
                        elif variacion <= -5:
                            estado = "🟡" 
                        elif variacion > 5:
                            estado = "🟠" 

                        # --- 🕒 LÓGICA DE COOLDOWN ---
                        ahora_utc = datetime.now(timezone.utc)
                        puedo_alertar = True
                        
                        if last_alert_str:
                            try:
                                last_alert_dt = datetime.fromisoformat(last_alert_str.replace('Z', '+00:00'))
                                if ahora_utc - last_alert_dt < timedelta(minutes=30):
                                    puedo_alertar = False
                            except Exception as e:
                                print(f"⚠ Error parseando last_alert_at: {e}")

                        # --- 🚀 DESPACHO DE NOTIFICACIONES ---
                        if estado in ["🟡", "🔴"] and puedo_alertar:
                            user_profile = caza.get("profiles")
                            
                            if isinstance(user_profile, list) and len(user_profile) > 0:
                                user_profile = user_profile[0]
                            
                            if not user_profile:
                                try:
                                    print(f"⚠️ Buscando perfil de emergencia en DB para: {caza.get('user_id')}")
                                    res_perfil = supabase.table("profiles").select("*").eq("user_id", caza.get("user_id")).execute()
                                    if res_perfil.data and len(res_perfil.data) > 0:
                                        user_profile = res_perfil.data[0]
                                except Exception as e:
                                    print(f"❌ Error buscando perfil: {e}")

                            # 🛠️ PUENTE DE RESPALDO (Hardcodeado para Alejandro)
                            if not user_profile:
                                print(f"🛠️ Usando perfil de respaldo manual para {caza.get('user_id')}")
                                user_profile = {
                                    "email": "howlify.app@gmail.com",
                                    "telegram_id": "8091046688",
                                    "plan": "business_monitor"
                                }

                            if user_profile and isinstance(user_profile, dict) and user_profile.get('email'):
                                print(f"📣 ¡GATILLO! Enviando notificación {estado} a {user_profile.get('email')}")
                                despachar_alertas_jauria(
                                    user_data=user_profile,
                                    producto=caza['producto'],
                                    estado=estado,
                                    precio_nuevo=precio_actual,
                                    variacion=variacion
                                )
                                update_data["last_alert_at"] = ahora_utc.isoformat()
                                update_data["last_alert_price"] = precio_actual
                            else:
                                print(f"❌ No se pudo recuperar data del usuario {caza.get('user_id')}")

                        update_data["ultimo_precio_detectado"] = precio_actual
                    else:
                        print(f"💨 Sin novedades para '{caza['producto']}'.")

                    # Actualizamos Supabase con los resultados del ciclo
                    supabase.table("cazas").update(update_data).eq("id", caza["id"]).execute()  
                    
            else:
                print("💤 Nada que cazar por ahora. Todo bajo control.")

        except Exception as e:
            print(f"❌ Error crítico en el ciclo del Worker: {e}")

        time.sleep(60)

def _handle_exit(signum, frame):
    print(f"\n🛑 Apagando el Lobo Guardián de forma segura... [Signal {signum}]")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)
    main()