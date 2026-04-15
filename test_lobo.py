from services.notification_service import despachar_alertas_jauria

# Simulamos los datos de un usuario Pro (para que pase el filtro de starter)
user_test = {
    "plan_id": "pro",
    "telegram_id": "8091046688", # Si querés probarlo también
    "email": "vazquezale82@gmail.com",
    "whatsapp_number": "5491158210746" # USA TU NÚMERO REAL ACÁ
}

print("🚀 Disparando alerta de prueba...")
despachar_alertas_jauria(
    user_data=user_test,
    producto="Monitor Gamer ThinkPad",
    estado="🔴", 
    precio_nuevo=150000,
    variacion=-15.5
)