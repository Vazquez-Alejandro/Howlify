import smtplib
import os
import requests
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
# 📧 CANAL EMAIL (Rescatado de engine.py)
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
# 🐺 EL DESPACHADOR (El cerebro que decide)
# ==========================================
def despachar_alertas_jauria(user_data, producto, estado, precio_nuevo, variacion):
    """
    Decide por qué canales enviar según el plan y el estado del semáforo.
    """
    plan = user_data.get('plan_id', 'starter').lower()
    t_id = user_data.get('telegram_id')
    email = user_data.get('email')
    
    # 📝 Mensaje formateado para Telegram
    msg_telegram = (
        f"{estado} *HOWLIFY ALERT*\n\n"
        f"📦 *Producto:* {producto}\n"
        f"💰 *Precio:* ${precio_nuevo:,}\n"
        f"📊 *Cambio:* {variacion:+.2f}%\n\n"
        f"🐺 _Enviado desde tu ThinkPad_"
    ).replace(",", ".")

    # 1. Notificar por Telegram (Todos los planes según tu decisión)
    if t_id:
        enviar_telegram(t_id, msg_telegram)

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

    # 3. WhatsApp (Lógica preparada para Pro/Business)
    if plan != "starter":
        # Aquí llamarías a la lógica de tu alertas.py
        print(f"✅ [Notificador] WhatsApp listo para plan {plan}")

def enviar_whatsapp(numero, mensaje):
    """
    🛠️ MOCK: Función preparada para el futuro envío por WhatsApp.
    Por ahora solo printea en consola para no romper el flujo.
    """
    print(f"📱 [PROXIMAMENTE] Simulando envío de WhatsApp a {numero}: {mensaje}")
    return True