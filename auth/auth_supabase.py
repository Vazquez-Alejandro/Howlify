from auth.supabase_client import supabase
import os
import re

# ==========================================================
# 🛠️ HELPERS DE VALIDACIÓN
# ==========================================================

def validar_password(password: str, confirm_password: str = None):
    """Chequea que la pass sea robusta y coincida."""
    if len(password) < 8:
        return "⚠️ La contraseña es muy corta (mínimo 8 caracteres)."
    
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "⚠️ La contraseña debe tener letras y números, che."

    if confirm_password is not None and password != confirm_password:
        return "⚠️ Las contraseñas no coinciden. Miralas bien."
    
    return None

# ==========================================================
# 🐺 REGISTRO DE CAZADORES
# ==========================================================

def supa_signup(email: str, password: str, confirm_password: str, username: str, plan: str):
    try:
        # 1. Validaciones previas
        pass_error = validar_password(password, confirm_password)
        if pass_error:
            return None, pass_error

        if not username or len(username) < 3:
            return None, "⚠️ Ese nombre de usuario es muy corto."

        email = email.strip().lower()
        username = username.strip()

        # 2. Intento de creación en Auth
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"username": username}}
        })

        if not res.user:
            return None, "❌ Error al crear el usuario. Probá de nuevo."

        # 3. Creación del Perfil
        try:
            supabase.table("profiles").insert({
                "user_id": res.user.id,
                "username": username,
                "email": email,
                "plan": (plan or "omega").strip().lower(),
                "role": "user"
            }).execute()
        except Exception as e_db:
            msg = str(e_db).lower()
            # Si es el error de RLS (42501) o permisos
            if "row-level security" in msg or "42501" in msg:
                return res.user, "⚠️ Cuenta creada, pero el perfil está en revisión. ¡Tranqui, ya podés confirmar tu mail!"
            
            # Si el username ya existe
            if "unique" in msg and "username" in msg:
                return res.user, "⚠️ El nombre de usuario ya está tomado. Elegí otro al confirmar."
                
            # Error genérico pero prolijo
            return res.user, "⚠️ Se creó la cuenta pero hubo un retraso en el perfil. Contactanos si no podés entrar."
        return res.user, None

    except Exception as e:
        msg = str(e).lower()
        if "already registered" in msg:
            return None, "📧 Ese email ya tiene dueño. ¿Te olvidaste la clave?"
        if "rate limit" in msg:
            return None, "🛑 ¡Pará un poco el carro! Demasiados intentos, esperá un ratito."
        return None, f"❌ Error: {str(e)}"

# ==========================================================
# 🔑 LOGIN (MULTIMODO: EMAIL O USERNAME)
# ==========================================================

def supa_login(identifier: str, password: str):
    try:
        id_clean = identifier.strip()
        final_email = id_clean

        if "@" not in id_clean:
            res_p = supabase.table("profiles").select("email").eq("username", id_clean).limit(1).execute()
            if not res_p.data:
                return None, "🕵️‍♂️ No encontramos a ningún cazador con ese nombre."
            final_email = res_p.data[0]["email"]

        res = supabase.auth.sign_in_with_password({
            "email": final_email.lower(),
            "password": password
        })

        if not res.user:
            return None, "❌ Login fallido. Chequeá los datos."

        return res.user, None

    except Exception as e:
        msg = str(e).lower()
        if "invalid login credentials" in msg:
            return None, "🔑 Pifiaste con el mail o la contraseña. Reintentá."
        if "email not confirmed" in msg:
            return None, "📧 ¡Ey! Primero confirmá el mail que te mandamos."
        return None, "❌ No se pudo entrar. Revisá tu conexión o los datos."

# ==========================================================
# 🛠️ RECUPERACIÓN
# ==========================================================

import os


def supa_reset_password(email: str):
    try:
        # Usa la URL de la APP si existe, sino fallback a la URL hardcodeada para deploy
        app_base_url = os.getenv("APP_URL", "https://howlify.onrender.com").rstrip("/")
        redirect = f"{app_base_url}/reset_password.html"

        supabase.auth.reset_password_for_email(email.strip().lower(), {"redirect_to": redirect})
        return True, "📧 ¡Listo! Te mandamos un link para resetear la clave."
    except Exception as e:
        return False, f"❌ Falló el envío: {str(e)}"