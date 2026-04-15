import os
import random
from datetime import datetime
# Importamos los clientes desde el archivo hermano usando el punto (.)
from .supabase_client import supabase, supabase_admin

def generar_sugerencias(username):
    """Genera 3 opciones de nick basadas en el original."""
    sufijos = [str(random.randint(10, 99)), "wolf", "dev", "cazador"]
    random.shuffle(sufijos)
    return [f"{username}_{s}" for s in sufijos[:3]]

def supa_signup(email, password, confirm_password, username, plan="starter"):
    """
    Registro optimizado: El perfil se crea automáticamente en Supabase
    gracias al Trigger SQL. Ya no hacemos el insert manual aquí.
    """
    try:
        if password != confirm_password:
            return None, "⚠️ Las contraseñas no coinciden."

        # 1. Verificar disponibilidad del Alias
        check = supabase_admin.table("profiles").select("username").eq("username", username).execute()
        if check.data:
            sugerencias = generar_sugerencias(username)
            return None, f"⚠️ El alias '{username}' ya está en uso. Probá con: {', '.join(sugerencias)}"

        # 2. Registro en Auth
        # Los metadatos 'username' y 'plan' son capturados por el Trigger en la DB
        res = supabase.auth.sign_up({
            "email": email.strip().lower(),
            "password": password,
            "options": {
                "data": {
                    "username": username.strip(),
                    "plan": plan
                }
            }
        })

        if res.user:
            # NO HACEMOS INSERT AQUÍ. El Trigger en Supabase ya lo hizo.
            return res.user, "✅ Registro exitoso. ¡Bienvenido a la jauría!"
        
        return None, "❌ No se pudo crear el usuario en Auth."
        
    except Exception as e:
        return None, f"❌ Error en registro: {str(e)}"

def supa_login(identifier, password):
    """Login Dual: Email o Alias."""
    try:
        final_email = identifier
        if "@" not in identifier:
            res_p = supabase_admin.table("profiles").select("email").eq("username", identifier).execute()
            if not res_p.data:
                return None, f"❌ No existe el alias '{identifier}'."
            final_email = res_p.data[0]["email"]

        res = supabase.auth.sign_in_with_password({
            "email": final_email.strip().lower(),
            "password": password
        })
        
        if res.user:
            return res.user, f"🐺 ¡Bienvenido, {identifier}!"
        return None, "❌ Credenciales inválidas."
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

def supa_logout():
    try:
        supabase.auth.sign_out()
        return True, "👋 Sesión cerrada."
    except Exception as e:
        return False, f"Error al cerrar sesión: {str(e)}"

def actualizar_alias(user_id, nuevo_username):
    try:
        check = supabase_admin.table("profiles").select("username").eq("username", nuevo_username).execute()
        if check.data:
            return False, "Ese alias ya está pillado."
        supabase_admin.table("profiles").update({"username": nuevo_username}).eq("user_id", user_id).execute()
        return True, "Alias actualizado."
    except Exception as e:
        return False, str(e)

def supa_reset_password(email):
    try:
        supabase.auth.reset_password_for_email(email.strip().lower())
        return True, "📧 Se envió un correo para restablecer tu contraseña."
    except Exception as e:
        return False, f"❌ Error al enviar correo: {str(e)}"