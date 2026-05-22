import os
import requests
from datetime import datetime

# ==========================================
# 📧 CANAL EMAIL (Vía Resend - Más estable)
# ==========================================
def enviar_email(destinatario, asunto, cuerpo_html):
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    
    if not api_key:
        print("❌ Resend: API Key no configurada en Render.")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": from_email,
        "to": destinatario,
        "subject": asunto,
        "html": cuerpo_html
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers)
        print(f"DEBUG MAIL: {r.status_code} - {r.text}")
        return r.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Error Email: {e}")
        return False

# ==========================================
# 🟦 CANAL TELEGRAM
# ==========================================
def enviar_telegram(chat_id, mensaje):
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("❌ Telegram: Token no configurado.")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": mensaje, 
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error Telegram: {e}")
        return False

# ==========================================
# 🟢 CANAL WHATSAPP (Vía Whapi - DEFINITIVO)
# ==========================================
def enviar_whatsapp(numero, mensaje):
    token = os.getenv("WHATSAPP_TOKEN")
    
    if not token or not numero:
        print("❌ WhatsApp: Token o número no configurados.")
        return False
        
    num_clean = "".join(filter(str.isdigit, str(numero)))
    url = "https://gate.whapi.cloud/messages/text"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "to": f"{num_clean}@s.whatsapp.net",
        "body": mensaje
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"DEBUG WHATSAPP: {response.status_code} - {response.text}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Error WhatsApp: {e}")
        return False

# ==========================================
# 🐺 EL DESPACHADOR
# ==========================================
def despachar_alertas_jauria(user_data, producto, estado, precio_nuevo, variacion):
    plan = user_data.get('plan_id', 'starter').lower()
    t_id = user_data.get('telegram_id')
    email = user_data.get('email')
    whatsapp_num = user_data.get('whatsapp_number')
    
    msg_alerta = (
        f"{estado} *HOWLIFY ALERT*\n\n"
        f"📦 *Producto:* {producto}\n"
        f"💰 *Precio:* ${precio_nuevo:,}\n"
        f"📊 *Cambio:* {variacion:+.2f}%\n\n"
        f"🐺 _Enviado desde Howlify_"
    ).replace(",", ".")

    # 1. Telegram
    if t_id:
        enviar_telegram(t_id, msg_alerta)

    # 2. Email
    if email:
        asunto = f"{estado} Alerta Howlify: {producto}"
        cuerpo = f"<h2>Reporte del Lobo 🐺</h2><p>El producto <b>{producto}</b> cambió a <b>{estado}</b>.</p>"
        enviar_email(email, asunto, cuerpo)

    # 3. WhatsApp (Solo planes Pro/Business)
    if plan != "starter" and whatsapp_num:
        enviar_whatsapp(whatsapp_num, msg_alerta)