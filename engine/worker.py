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

def despachar_alertas_jauria(user_data, producto, estado, precio_nuevo, variacion):
    """
    🐺 El Lobo decide por dónde avisar según el plan y el semáforo.
    """
    plan = user_data.get('plan_id', 'starter').lower()
    t_id = user_data.get('telegram_id')
    email = user_data.get('email')
    
    # Emoji y mensaje unificado
    msg = (
        f"{estado} *HOWLIFY ALERT*\n\n"
        f"📦 *Producto:* {producto}\n"
        f"💰 *Precio:* ${precio_nuevo:,}\n"
        f"📊 *Cambio:* {variacion:+.2f}%\n\n"
        f"🐺 _Enviado desde tu ThinkPad_"
    ).replace(",", ".")

    # 🟦 TELEGRAM: Para todos (Starter, Pro, Business)
    if t_id:
        try:
            enviar_telegram(t_id, msg)
            print(f"📱 [Notificador] Telegram enviado a {t_id}")
        except Exception as e:
            print(f"❌ Error enviando Telegram: {e}")

    # 📧 EMAIL: Para todos (Foco preventivo en Amarillo/Naranja)
    if email and estado in ["🟡", "🟠", "🔴"]:
        try:
            enviar_email_alerta(email, producto, estado, precio_nuevo, variacion)
            print(f"📧 [Notificador] Email enviado a {email}")
        except Exception as e:
            print(f"❌ Error enviando Email: {e}")

    # 🟩 WHATSAPP: Solo si NO es Starter (El gancho del Pro/Business)
    if plan != "starter":
        # wa.enviar_mensaje(user_data.get('phone'), msg)
        print(f"✅ [Notificador] WhatsApp saltado (Lógica preparada para {plan})")

def obtener_cazas_pendientes():
    """
    Busca cacerías sincronizadas por bloques de tiempo (00, 15, 30, 45).
    """
    ahora = datetime.now(timezone.utc)
    minuto_actual = ahora.minute
    
    query = supabase.table("cazas").select("*, profiles(email, telegram_id, plan_id, whatsapp_number)").eq("estado", "activa").execute()
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
            cazas = obtener_cazas_pendientes() # <-- Asegurate que esta traiga el join de 'profiles'
            
            if cazas:
                print(f"🎯 Encontradas {len(cazas)} cacerías vencidas. Lanzando jauría...")
                for caza in cazas:
                    print(f"🔎 Procesando: {caza['producto']} (ID: {caza['id']})")
                    
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

                    update_data = {
                        "last_check": datetime.now(timezone.utc).isoformat()
                    }

                    if resultados:
                        precio_actual = resultados[0].get("price")
                        print(f"✅ Presas detectadas ({len(resultados)}) para '{caza['producto']}'. Precio: ${precio_actual}")
                        
                        # --- 🐺 LÓGICA DE SEMÁFORO Y GATILLO ---
                        estado = None
                        hubo_cambio_relevante = False
                        variacion = 0

                        if precio_anterior:
                            variacion = ((precio_actual - precio_anterior) / precio_anterior) * 100

                        # 🟢 Caso 1: ¡Llegamos al objetivo!
                        if precio_actual <= precio_objetivo:
                            estado = "🟢"
                            print(f"🎯 ¡OBJETIVO ALCANZADO! {caza['producto']} (VERDE 🟢)")
                            # Notificamos si es la primera vez que baja del objetivo
                            if not precio_anterior or precio_anterior > precio_objetivo:
                                hubo_cambio_relevante = True
                        
                        # 🔴 Caso 2: El precio SUBIÓ (Inflación)
                        elif precio_anterior and precio_actual > precio_anterior:
                            estado = "🔴"
                            print(f"⚠️ AVISO DE AUMENTO: {caza['producto']} subió {variacion:.1f}% (ROJO 🔴)")
                            hubo_cambio_relevante = True
                        
                        # 🟡 Caso 3: El precio BAJÓ pero no al objetivo todavía
                        elif precio_anterior and precio_actual < precio_anterior:
                            estado = "🟡"
                            print(f"📉 REBAJA DETECTADA: {caza['producto']} bajó {variacion:.1f}% (AMARILLO 🟡)")
                            hubo_cambio_relevante = True

                        # --- 🚀 DESPACHO DE NOTIFICACIONES ---
                        if hubo_cambio_relevante and estado:
                            # Sacamos los datos del perfil que vienen por el Join de Supabase
                            user_profile = caza.get("profiles", {})
                            if user_profile:
                                despachar_alertas_jauria(
                                    user_data=user_profile,
                                    producto=caza['producto'],
                                    estado=estado,
                                    precio_nuevo=precio_actual,
                                    variacion=variacion
                                )

                        update_data["ultimo_precio_detectado"] = precio_actual
                    else:
                        print(f"💨 Sin novedades para '{caza['producto']}'.")

                    # Actualizamos Supabase
                    supabase.table("cazas").update(update_data).eq("id", caza["id"]).execute()  
                    
            else:
                print("💤 Nada que cazar por ahora. Todo bajo control.")

        except Exception as e:
            print(f"❌ Error crítico en el ciclo del Worker: {e}")

        # Chequeamos cada 60 segundos
        time.sleep(60)

def _handle_exit(signum, frame):
    print(f"\n🛑 Apagando el Lobo Guardián de forma segura... [Signal {signum}]")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)
    main()