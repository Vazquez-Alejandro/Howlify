import smtplib
import os
import requests
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ==========================================
# CONFIGURACIÓN (Ajustada a tu .env)
# ==========================================
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASSWORD", "")
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN", "") 

# ==========================================
# 📧 CANAL EMAIL
# ==========================================
def enviar_email(destinatario, asunto, cuerpo_html):
    if not SMTP_USER or not SMTP_PASS:
        print("❌ SMTP: Credenciales no configuradas.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Howlify Alertas 🐺 <{SMTP_USER}>"
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo_html, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Error SMTP: {e}")
        return False

# ==========================================
# 🟦 CANAL TELEGRAM
# ==========================================
def enviar_telegram(chat_id, mensaje):
    if not TOKEN_TELEGRAM:
        print("❌ Telegram: Token no configurado.")
        return
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": mensaje, 
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Error Telegram: {e}")

# ==========================================
# 🟢 CANAL WHATSAPP (Vía Mudslide)
# ==========================================
def enviar_whatsapp(numero, mensaje):
    """
    🚀 ENVÍO REAL: Versión blindada para Linux.
    """
    if not numero:
        return False
        
    # Limpiamos el número por las dudas (solo números)
    num_clean = "".join(filter(str.isdigit, str(numero)))
    
    try:
        # Usamos una lista de argumentos y shell=False es más seguro, 
        # pero si npx no está en el path de Python, usamos el comando directo:
        comando = f'npx mudslide send {num_clean} "{mensaje}"'
        
        # Ejecutamos
        subprocess.run(comando, shell=True, check=True)
        
        print(f"✅ [WhatsApp] Comando ejecutado para {num_clean}")
        return True
    except Exception as e:
        print(f"❌ Error en subprocess: {e}")
        return False
    

# ==========================================
# 🐺 EL DESPACHADOR (El cerebro que decide)
# ==========================================
def despachar_alertas_jauria(user_data, producto, estado, precio_nuevo, variacion):
    """
    Decide por qué canales enviar según el plan y el estado del semáforo.
    """
    plan = user_data.get('plan_id', 'starter').lower()
    t_id = user_data.get('telegram_id')
    email = user_data.get('email')
    whatsapp_num = user_data.get('whatsapp_number') # Extraemos el número del dict
    
    # 📝 Mensaje formateado para Telegram y WhatsApp
    msg_alerta = (
        f"{estado} *HOWLIFY ALERT*\n\n"
        f"📦 *Producto:* {producto}\n"
        f"💰 *Precio:* ${precio_nuevo:,}\n"
        f"📊 *Cambio:* {variacion:+.2f}%\n\n"
        f"🐺 _Enviado desde tu ThinkPad_"
    ).replace(",", ".")

    # 1. Notificar por Telegram
    if t_id:
        enviar_telegram(t_id, msg_alerta)

    # 2. Notificar por Email (Solo si es preventivo/crítico)
    if email and estado in ["🟡", "🟠", "🔴"]:
        asunto = f"{estado} Alerta Howlify: {producto}"
        cuerpo = f"""
        <h2>Reporte del Lobo 🐺</h2>
        <p>El producto <b>{producto}</b> ha cambiado de estado a <b>{estado}</b>.</p>
        <ul>
            <li>Precio: ${precio_nuevo:,}</li>
            <li>Variación: {variacion:+.2f}%</li>
        </ul>
        """
        enviar_email(email, asunto, cuerpo)

    # 3. WhatsApp (REAL para planes que no sean Starter)
    if plan != "starter" and whatsapp_num:
        enviar_whatsapp(whatsapp_num, msg_alerta)
    elif plan != "starter" and not whatsapp_num:
        print(f"⚠️ [Notificador] Plan {plan} requiere WhatsApp pero no hay número.")