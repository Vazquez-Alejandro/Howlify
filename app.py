import os
import sys
import base64
import subprocess
import time
import re
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from urllib.parse import urlparse


import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Forzamos la ruta del navegador por código para que no dependa solo de Render
#os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.getcwd(), "pw-browsers")

# ==========================================================
# 🛡️ 1. CONFIGURACIÓN ESTRATÉGICA (SIEMPRE PRIMERO)
# ==========================================================
# Esto tiene que ir antes de cualquier import local para evitar el error de Render
st.set_page_config(
    page_title="Howlify· Price Intelligence", 
    layout="centered", 
    page_icon="🐺",
    initial_sidebar_state="expanded"
)
# Cargamos el .env antes de importar los módulos que usan API Keys
load_dotenv()

# ==========================================================
# 🚀 2. IMPORTS DE LÓGICA (POST-CONFIG)
# ==========================================================
print("🚀 APP REINICIADA - IMPORTANDO MÓDULOS...")

from auth.supabase_client import supabase 
from auth.auth_supabase import supa_signup, supa_login, supa_reset_password
from scraper.scraper_pro import hunt_offers
from config import PLAN_LIMITS
from services.business_service import obtener_top_oportunidades
from services.whatsapp_service import enviar_whatsapp
from services.telegram_service import enviar_telegram
from utils.affiliate import get_affiliate_url

# --- 🛠️ SERVICIOS DE BASE DE DATOS ---
# Centralizamos guardar_caza_supabase aquí, que es donde vive ahora
from services.database_service import guardar_caza_supabase

from db.database import (
    obtener_cazas, 
    save_user_telegram, 
    get_user_profile
)

# --- 🧠 UTILIDADES Y LÓGICA ---
# Borramos guardar_caza_supabase de aquí porque ya no existe en este archivo
from utils.logic import (
    normalize_plan_family,
    clean_ml_url, 
    upsert_monitor_rule 
)

# ==========================================================
# ⚙️ 3. CONSTANTES Y RUTAS
# ==========================================================
DEBUG = os.getenv("DEBUG", "0") == "1"
BASE_DIR = os.path.dirname(__file__)

# Rutas de Assets
WOLF_PATH = os.path.join(BASE_DIR, "assets", "wolf.mp3")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "img", "logo.png")

# Configuración Scraper
DEFAULT_SOURCE = "generic"
FORCE_HEADLESS = True

# Debug Log
if DEBUG:
    st.sidebar.info("🔧 Modo Debug Activo")

# ==========================================================
# UTILIDADES: PROCESAMIENTO DE IMÁGENES (BASE64)
# ==========================================================

def get_image_base64(path):
    """
    Convierte una imagen local en una cadena Base64 para bypass de seguridad 
    del navegador y visualización directa en Streamlit.
    """
    if not path:
        return None
        
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                # Leemos el binario y lo encodeamos a texto
                return base64.b64encode(f.read()).decode()
        except Exception as e:
            print(f"⚠️ Error al procesar imagen Base64: {e}")
            return None
    return None


# --- DETECTOR DE RECOVERY CON ESTILO HOWLIFY ---
params = st.query_params
if params.get("type") == "recovery" and "token" in params:
    # Centramos el formulario
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>🐺 Howlify</h1>", unsafe_allow_html=True)
        st.subheader("🔑 Restablecer Contraseña")
        st.info("Ingresá tu nueva clave para volver a la jauría.")
        
        with st.container(border=True):
            nueva_pass = st.text_input("Nueva contraseña", type="password", placeholder="Mínimo 8 caracteres, letra y número")
            confirmar = st.text_input("Confirmar contraseña", type="password", placeholder="Repetí tu contraseña")
            
            st.markdown("---")
            if st.button("Actualizar y Entrar", use_container_width=True, type="primary"):
                if nueva_pass == confirmar and len(nueva_pass) >= 8:
                    try:
                        # Validación del token
                        supabase.auth.verify_otp({
                            "token_hash": params.get("token"),
                            "type": "recovery"
                        })
                        # Cambio de password
                        supabase.auth.update_user({"password": nueva_pass})
                        
                        st.success("¡Contraseña actualizada con éxito!")
                        st.balloons() # Un poco de festejo por las 4 horas de pelea
                        time.sleep(2)
                        st.query_params.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"El link venció o es inválido: {e}")
                else:
                    st.error("Las claves no coinciden o no cumplen los requisitos (min 8 caracteres).")
                    
        if st.button("Cancelar", use_container_width=True):
            st.query_params.clear()
            st.rerun()
            
    st.stop() # Bloqueo total del resto de la app

    # --- DETECTOR DE CONFIRMACIÓN DE REGISTRO (SIGNUP) ---
if params.get("type") == "signup" and "token" in params:
    st.markdown("<h1 style='text-align: center;'>🐺 ¡Bienvenido a Howlify!</h1>", unsafe_allow_html=True)
    st.info("Estamos verificando tu cuenta...")
    
    try:
        # Validamos el token de registro
        supabase.auth.verify_otp({
            "token_hash": params.get("token"),
            "type": "signup"
        })
        st.success("¡Cuenta confirmada con éxito! Ya podés iniciar sesión.")
        st.balloons()
        time.sleep(3)
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Error al confirmar la cuenta: {e}")
        if st.button("Ir al Login"):
            st.query_params.clear()
            st.rerun()
    st.stop()

# ==========================================================
# SESSION STATE
# ==========================================================

if "busquedas" not in st.session_state:
    st.session_state["busquedas"] = []
if "forms_extra" not in st.session_state:
    st.session_state["forms_extra"] = 0
if "ws_vinculado" not in st.session_state:
    st.session_state["ws_vinculado"] = False
if "sound_enabled" not in st.session_state:
    st.session_state["sound_enabled"] = True
if "sound_tick" not in st.session_state:
    st.session_state["sound_tick"] = 0
if "play_sound" not in st.session_state:
    st.session_state["play_sound"] = False
if "product_type" not in st.session_state:
    st.session_state["product_type"] = None
if "plan_elegido" not in st.session_state:
    st.session_state["plan_elegido"] = None



# ==========================================================
#LÓGICA PARA EL DIÁLOGO DE EDICIÓN
# ==========================================================
if "editing_caza" in st.session_state and st.session_state["editing_caza"] is not None:
    caza = st.session_state["editing_caza"]
    
    # Título del diálogo: usamos n_key para mostrar, pero no para guardar
    label_dialogo = caza.get('n_key') or caza.get('keyword') or 'Cacería'
    
    @st.dialog(f"✏️ Editando: {label_dialogo}")
    def show_edit_dialog(c_data):
        rid = c_data.get('id')
        
        # Inputs del formulario
        nuevo_nombre = st.text_input("Nombre / Etiqueta", 
                                    value=c_data.get("keyword") or "", 
                                    key=f"edit_name_{rid}")
        
        nueva_url = st.text_input("URL del producto/vuelo", 
                                  value=c_data.get("url", ""), 
                                  key=f"edit_url_{rid}")
        
        p_actual = c_data.get("precio_max") or 0
        nuevo_precio = st.number_input("Precio Máximo (ARS)", 
                                       value=int(p_actual), 
                                       step=1000, 
                                       key=f"edit_price_{rid}")
        
        st.divider()
        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("💾 Guardar", use_container_width=True, type="primary"):
                try:
                    # 1. DATA PURA PARA LA BASE DE DATOS (Usando los nombres reales)
                    data_db = {
                        "producto": nuevo_nombre if nuevo_nombre else c_data.get("producto"), # ACÁ ESTABA EL ERROR VISUAL
                        "keyword": nuevo_nombre if nuevo_nombre else c_data.get("keyword"),
                        "link": nueva_url if nueva_url else c_data.get("link"), # Tu DB usa 'link', no 'url'
                        "precio_max": nuevo_precio if nuevo_precio > 0 else c_data.get("precio_max")
                    }
                    
                    # Filtramos Nones
                    data_db = {k: v for k, v in data_db.items() if v is not None}

                    res = supabase.table("cazas").update(data_db).eq("id", rid).execute()
                    print("👉 RESULTADO SUPABASE:", res.data, " | ID BUSCADO:", rid)
                    
                    # 2. FORZAMOS A STREAMLIT A ACTUALIZAR EL DASHBOARD
                    st.session_state["editing_caza"] = None
                    st.cache_data.clear() # Obliga a volver a leer de Supabase
                    
                    # Borramos la lista vieja de la memoriaa
                    if "busquedas" in st.session_state:
                        del st.session_state["busquedas"]

                    st.success("¡Guardado!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
        
        with c2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state["editing_caza"] = None
                st.rerun()

    show_edit_dialog(caza)

# ==========================================================
# PLANES / COMPATIBILIDAD
# ==========================================================

PLAN_ALIAS = {
    "omega": "starter",
    "trial": "starter",
    "starter": "starter",
    "beta": "pro",
    "alfa": "pro",
    "revendedor": "pro",
    "empresa": "pro",
    "pro": "pro",
    "business_reseller": "business_reseller",
    "business_monitor": "business_monitor",
}


def normalize_plan_family(plan: str) -> str:
    raw = (plan or "starter").strip().lower()
    return PLAN_ALIAS.get(raw, "starter")


def plan_label(plan: str):
    raw = (plan or "").strip().lower()

    if raw == "business_reseller":
        return "Business Reseller"
    if raw == "business_monitor":
        return "Business Monitor"

    fam = normalize_plan_family(plan)
    return "Starter" if fam == "starter" else "Pro"


def get_effective_plan_rules(plan: str) -> dict:
    fam = normalize_plan_family(plan)

    if fam == "starter":
        return {
            "plan_key": "starter",
            "label": "Starter",
            "max_cazas_activas": 5,
            "min_interval_minutes": 60,
            "freq_options": ["1 h", "2 h", "4 h", "12 h"],
            "notifications": ["email"],
            "stores": ["mercadolibre", "generic"],
            "features": {
                "dashboard_empresa": False,
                "export_csv": False,
                "multi_store_same_hunt": False,
                "whatsapp_alerts": False,
                "business_mode": False,
                "business_rankings": False,
            },
        }

    if fam == "business_reseller":
        return {
            "plan_key": "business_reseller",
            "label": "Business Reseller",
            "max_cazas_activas": 50,
            "min_interval_minutes": 15,
            "freq_options": ["15 min", "30 min", "45 min", "1 h", "2 h"],
            "notifications": ["email", "whatsapp"],
            "stores": ["mercadolibre", "generic"],
            "features": {
                "dashboard_empresa": True,
                "export_csv": True,
                "multi_store_same_hunt": True,
                "whatsapp_alerts": True,
                "business_mode": True,
                "business_rankings": True,
            },
        }

    if fam == "business_monitor":
        return {
            "plan_key": "business_monitor",
            "label": "Business Monitor",
            "max_cazas_activas": 100,
            "min_interval_minutes": 15,
            "freq_options": ["15 min", "30 min", "45 min", "1 h", "2 h"],
            "notifications": ["email", "whatsapp"],
            "stores": ["mercadolibre", "generic"],
            "features": {
                "dashboard_empresa": True,
                "export_csv": True,
                "multi_store_same_hunt": True,
                "whatsapp_alerts": True,
                "business_mode": True,
                "business_rankings": True,
            },
        }

    return {
        "plan_key": "pro",
        "label": "Pro",
        "max_cazas_activas": 15,
        "min_interval_minutes": 15,
        "freq_options": ["15 min", "30 min", "45 min", "1 h", "2 h"],
        "notifications": ["email", "whatsapp"],
        "stores": ["mercadolibre", "generic"],
        "features": {
            "dashboard_empresa": False,
            "export_csv": True,
            "multi_store_same_hunt": True,
            "whatsapp_alerts": True,
            "business_mode": False,
            "business_rankings": False,
        },
    }


# ==========================================================
# HELPERS
# ==========================================================
def calc_result_score(item: dict, min_price: int, avg_price: float) -> float:
    """
    Score relativo al lote actual:
    - más score si está cerca del mínimo
    - más score si está bastante por debajo del promedio
    - pequeño bonus por título más limpio/corto
    """
    try:
        price = int(item.get("price") or item.get("precio") or 999999999)
    except Exception:
        price = 999999999

    title = str(item.get("title") or item.get("titulo") or "").strip()

    title_len_bonus = 0
    if title:
        if len(title) <= 55:
            title_len_bonus = 10
        elif len(title) <= 85:
            title_len_bonus = 5

    if price <= 0 or avg_price <= 0 or min_price <= 0:
        return round(title_len_bonus, 2)

    # qué tan cerca está del mínimo
    min_component = max(0, (min_price / price) * 40)

    # qué tan por debajo del promedio está
    diff_vs_avg_pct = ((avg_price - price) / avg_price) * 100
    avg_component = max(0, diff_vs_avg_pct * 2.2)

    return round(min_component + avg_component + title_len_bonus, 2)


def get_result_badge(item: dict, min_price: int, avg_price: float) -> tuple[str, str]:
    """
    Badge dinámico según el lote actual.
    """
    try:
        price = int(item.get("price") or item.get("precio") or 0)
    except Exception:
        price = 0

    if price <= 0 or avg_price <= 0:
        return ("📦", "Sin precio claro")

    diff_vs_avg_pct = ((avg_price - price) / avg_price) * 100

    if price == min_price:
        return ("🏆", "Más barato del lote")
    if diff_vs_avg_pct >= 20:
        return ("🔥", "Oportunidad")
    if diff_vs_avg_pct >= 10:
        return ("💰", "Buen precio")
    if diff_vs_avg_pct >= 0:
        return ("👀", "Para seguir")
    return ("📌", "Por encima del promedio")


def sort_results_intelligent(results: list[dict]) -> list[dict]:
    cleaned = []
    seen = set()

    for item in results or []:
        title = str(item.get("title") or item.get("titulo") or "").strip()
        link = str(item.get("url") or item.get("link") or "").strip()

        try:
            price = int(item.get("price") or item.get("precio") or 999999999)
        except Exception:
            price = 999999999

        key = (title.lower(), price, link)
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(item)

    valid_prices = []
    for item in cleaned:
        try:
            p = int(item.get("price") or item.get("precio") or 0)
            if p > 0 and p < 999999999:
                valid_prices.append(p)
        except Exception:
            pass

    min_price = min(valid_prices) if valid_prices else 0
    avg_price = sum(valid_prices) / len(valid_prices) if valid_prices else 0

    for item in cleaned:
        item["_score"] = calc_result_score(item, min_price, avg_price)
        item["_min_price"] = min_price
        item["_avg_price"] = avg_price

    cleaned.sort(
        key=lambda x: (
            -(x.get("_score") or 0),
            int(x.get("price") or x.get("precio") or 999999999),
        )
    )
    return cleaned

def password_strength(password: str):
    score = 0

    if len(password) >= 8:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1

    if score <= 2:
        return "Débil", "🔴"
    if score <= 4:
        return "Media", "🟠"
    return "Fuerte", "🟢"


def domain_from_url(url: str) -> str:
    try:
        host = urlparse(str(url)).netloc.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        return host or "unknown"
    except Exception:
        return "unknown"


def infer_source_from_url(url: str) -> str:
    d = domain_from_url(url)
    if "mercadolibre" in d:
        return "mercadolibre"
    if "fravega" in d:
        return "fravega"
    if "garbarino" in d:
        return "garbarino"
    if "tiendamia" in d:
        return "tiendamia"
    if "temu" in d:
        return "temu"
    if "tripstore" in d:
        return "tripstore"
    if "carrefour" in d:
        return "carrefour"
    if "despegar" in d:
        return "despegar"
    return "unknown"


def parse_price_to_int(value) -> int:
    if value is None:
        return 0

    if isinstance(value, int):
        return int(value)

    if isinstance(value, float):
        return int(value)

    s = str(value).strip()
    if not s:
        return 0

    if re.fullmatch(r"\d+\.\d{1,2}", s):
        s = s.split(".", 1)[0]

    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return 0

    try:
        return int(digits)
    except Exception:
        return 0

def save_price_history(user_id: str, caza_id, results: list[dict]) -> None:
    if not user_id or not results:
        return

    rows = []

    for r in results:
        try:
            price = int(r.get("price") or r.get("precio") or 0)
        except Exception:
            price = 0

        if price <= 0:
            continue

        rows.append({
            "caza_id": caza_id,
            "user_id": user_id,
            "title": (r.get("title") or r.get("titulo") or "").strip(),
            "url": (r.get("url") or r.get("link") or "").strip(),
            "source": (r.get("source") or "").strip(),
            "price": price,
            "checked_at": "now()",
        })

    if not rows:
        return

    try:
        supabase.table("price_history").insert(rows).execute()
    except Exception as e:
        print("[save_price_history] error:", e)


def normalize_phone(number: str) -> str:
    return re.sub(r"\D", "", str(number or "").strip())


def get_base64_logo(path: str) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""


def play_wolf_sound():
    try:
        with open(WOLF_PATH, "rb") as f:
            audio_bytes = f.read()
        b64 = base64.b64encode(audio_bytes).decode()
        tick = int(st.session_state.get("sound_tick", 0))
        components.html(
            f"""
            <audio autoplay="true" style="display:none" id="wolf_{tick}">
              <source src="data:audio/mp3;base64,{b64}" type="audio/mp3" />
            </audio>
            """,
            height=0,
        )
    except Exception:
        pass

def mostrar_tarjeta_oportunidad(id_rastreo, titulo, precio_actual, precio_min_historico, precio_reventa_usuario):
    margen_bruto = precio_reventa_usuario - precio_actual
    porcentaje_ganancia = (margen_bruto / precio_actual) * 100 if precio_actual > 0 else 0
    diferencia_historica = precio_actual - precio_min_historico
    
    with st.container(border=True):
        st.markdown(f"#### 📦 {titulo}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="Precio Detectado", 
                value=f"${precio_actual:,.0f}".replace(",", "."), 
                delta=f"${abs(diferencia_historica):,.0f} {'arriba del' if diferencia_historica > 0 else 'debajo del'} mínimo", 
                delta_color="inverse" if diferencia_historica > 0 else "normal"
            )
        with col2:
            st.metric(label="Tu Precio de Reventa", value=f"${precio_reventa_usuario:,.0f}".replace(",", "."))
        with col3:
            if margen_bruto > 0:
                st.success(f"🔥 Margen: ${margen_bruto:,.0f} ({porcentaje_ganancia:.1f}%)")
            else:
                st.error("⚠️ No rentable a este precio")
                
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
        with btn_col1:
            st.button("✏️ Editar", key=f"edit_{id_rastreo}", use_container_width=True)
        with btn_col2:
            st.button("🗑️ Eliminar", key=f"del_{id_rastreo}", type="primary", use_container_width=True)
        with btn_col3:
            st.button("📲 Activar Alerta WhatsApp", key=f"wa_{id_rastreo}", use_container_width=True)
            
def render_profile_section(user_email, plan_actual):
    st.markdown("## 👤 Mi Perfil y Configuración")
    st.markdown("---")
    
    tab_cuenta, tab_plan, tab_ayuda = st.tabs(["Mi Cuenta", "💳 Plan y Pagos", "🛠️ Soporte y Ayuda"])
    
    with tab_cuenta:
        st.subheader("Datos del cazador")
        st.text_input("Correo electrónico", value=user_email, disabled=True)
        st.write("")
        
        if st.button("🚪 Cerrar Sesión", type="primary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    with tab_plan:
        st.subheader("Suscripción Actual")
        st.info(f"**Plan Activo:** {plan_actual} 🐺")
        st.write("Gestioná tu capacidad de cacería y métodos de pago.")
        col1, col2 = st.columns(2)
        with col1:
            
            if st.button("🚀 Cambiar o Mejorar Plan", use_container_width=True):
                st.toast("En breve: Redirigiendo a MercadoPago/Stripe...")
        with col2:
          
            if st.button("📄 Historial de Facturas", use_container_width=True):
                st.toast("En breve: Abriendo portal de facturación...")

    with tab_ayuda:
        st.subheader("Reportar problemas")
        st.write("¿El sabueso no logra rastrear una página o te tira error? Pasanos el link y lo entrenamos.")
        
        with st.form("form_soporte"):
            url_rota = st.text_input("🔗 URL de la página con problemas")
            descripcion = st.text_area("📝 Describí el problema", placeholder="Ej: Me dice que el precio es 0, o no detecta el producto...")
            
            col_submit, _ = st.columns([1, 2])
            with col_submit:
                # Este ya estaba bien (use_container_width=True)
                enviado = st.form_submit_button("Enviar Reporte", use_container_width=True)
            
            if enviado:
                if url_rota and descripcion:
                    st.success("✅ ¡Reporte enviado! La manada técnica lo revisará en breve.")
                else:
                    st.error("⚠️ Por favor, completá la URL y la descripción para que podamos ayudarte.")

def render_footer():
    st.markdown("---") # Línea divisoria sutil
    footer_html = """
    <div style="text-align: center; padding: 20px; color: #888; font-family: sans-serif;">
        <p style="margin-bottom: 10px; font-size: 16px;">
            <strong>Howlify 🐺</strong> | La manada cazando las mejores oportunidades
        </p>
        <p style="font-size: 22px; margin-bottom: 10px;">
            <a href="https://instagram.com/tu_cuenta" target="_blank" style="text-decoration: none; margin: 0 10px; color: #E1306C;" title="Instagram">📸</a>
            <a href="https://twitter.com/tu_cuenta" target="_blank" style="text-decoration: none; margin: 0 10px; color: #1DA1F2;" title="Twitter">🐦</a>
            <a href="https://facebook.com/tu_cuenta" target="_blank" style="text-decoration: none; margin: 0 10px; color: #1877F2;" title="Facebook">📘</a>
            <a href="https://youtube.com/tu_cuenta" target="_blank" style="text-decoration: none; margin: 0 10px; color: #FF0000;" title="YouTube">🎥</a>
        </p>
        <p style="font-size: 14px; margin-bottom: 5px;">
            ✉️ Contacto y Soporte: <a href="mailto:soporte@howlify.app" style="color: #0078D7; text-decoration: none;">soporte@howlify.app</a>
        </p>
        <p style="font-size: 12px; margin-top: 15px; opacity: 0.7;">
            © 2026 Howlify. Todos los derechos reservados. <br>
            Hecho para los revendedores de LATAM.
        </p>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

def render_business_monitor_dashboard(plan_label_text, user_id, busquedas):
    st.subheader(f"📊 Control de Precios · Monitor ({plan_label_text})")
    st.caption("🔒 Supervisá el cumplimiento de precios y salud de canal en tiempo real.")

    if not busquedas:
        st.warning("No hay productos monitoreados.")
        return

    st.markdown("### 📡 Radar de Precios Global")
    st.caption("Hacé clic en una fila para cargar el análisis detallado abajo.")

    # ==========================================================
    # 1. TRAER REGLAS (MAPEO UNIFICADO)
    # ==========================================================
    rules_res = supabase.table("monitor_rules").select("*").eq("user_id", user_id).execute()
    rules_data = rules_res.data or []
    
    rules_map = {str(r.get("caza_id")): r for r in rules_data if r.get("caza_id")}
    rules_by_url = {str(r.get("product_url")): r for r in rules_data if r.get("product_url")}

    radar_rows = []
    for b in busquedas:
        # 1. Limpieza de ID y Filtro Anti-Crash (Evita el error de bigint)
        bid = str(b.get("id") or "").strip()
        if not bid or not bid.isdigit():
            continue
            
        p_url = b.get("link") or b.get("url") or ""
        
        # 2. Mapeo de reglas
        rule = rules_map.get(bid) or rules_by_url.get(p_url) or {}
        
        # 3. Consulta de precio (Segura con bid validado)
        res_p = supabase.table("price_history").select("price").eq("caza_id", bid).order("checked_at", desc=True).limit(1).execute()
        curr_p = float(res_p.data[0]["price"]) if res_p.data else 0.0
        
        m_p = float(rule.get("min_price_allowed") or 0.0)
        max_p = float(rule.get("max_price_allowed") or 0.0)

        # 4. SEMÁFORO
        if curr_p <= 0: 
            riesgo = "⚪"
        elif m_p > 0 and curr_p < (m_p - 0.01):
            riesgo = "🔴" 
        elif max_p > 0 and curr_p > (max_p + 0.01):
            riesgo = "🟠"
        elif m_p == 0 and max_p == 0:
            riesgo = "⚪"
        else:
            riesgo = "🟢"

        # 5. PROGRESO
        progreso = 0.0
        if m_p > 0 and max_p > m_p:
            progreso = max(0.0, min(1.0, (curr_p - m_p) / (max_p - m_p)))

        # 6. 📸 LÓGICA DE EVIDENCIA: Extraemos la ruta del objeto 'b'
        foto_path = b.get("screenshot")
        evidencia_val = "📸 Ver" if (riesgo == "🔴" and foto_path) else ""

        # 7. ARMADO DE FILA (Con ID para la visualización)
        radar_rows.append({
            "Riesgo": riesgo,
            "ID": bid,
            "Producto": (b.get("producto") or b.get("keyword") or "SIN NOMBRE").upper(),
            "Precio": curr_p,
            "Mín. MAP": m_p,
            "Máximo": max_p,
            "Evidencia": evidencia_val,
            "Rango": progreso,
            "URL": p_url,
            "raw_data": b,
            "full_id": bid
        })

    # ==========================================================
    # 2. RENDER DE TABLA Y VISUALIZADOR DE EVIDENCIA
    # ==========================================================
    df_radar = pd.DataFrame(radar_rows)
    
    if not df_radar.empty:
        # Ordenamos por severidad del riesgo
        orden_prioridad = {"🔴": 0, "🟠": 1, "🟡": 2, "🟢": 3, "⚪": 4}
        df_radar["orden"] = df_radar["Riesgo"].map(orden_prioridad)
        df_radar = df_radar.sort_values("orden")

        # Limpiamos columnas de proceso para la vista de tabla
        df_display = df_radar.drop(columns=["raw_data", "full_id", "orden"], errors='ignore')

        # RENDER DE LA TABLA
        st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            key="radar_table_business_vFinal",
            disabled=True,
            column_config={
                "Riesgo": st.column_config.TextColumn("Riesgo", width="small"),
                "Producto": st.column_config.TextColumn("Producto", width="medium"),
                "Precio": st.column_config.NumberColumn("Precio", format="$%d"),
                "Mín. MAP": st.column_config.NumberColumn("Mín. MAP", format="$%d"),
                "Máximo": st.column_config.NumberColumn("Máximo", format="$%d"),
                "Evidencia": st.column_config.TextColumn("Evidencia", width="small"),
                "Rango": st.column_config.ProgressColumn("Posición", min_value=0, max_value=1),
                "URL": st.column_config.LinkColumn("Enlace", width="small"),
                "ID": st.column_config.TextColumn("ID", width="small"),
            },
            column_order=("Riesgo", "ID", "Producto", "Precio", "Mín. MAP", "Máximo", "Evidencia", "Rango", "URL")
        )

        st.divider() # Una línea sutil para separar la tabla de la foto

        # --- BLOQUE DE VISUALIZACIÓN DE FOTO (Base64) ---
        # Filtramos solo los productos que tienen el emoji de cámara
        con_evidencia = df_radar[df_radar["Evidencia"] != ""]["Producto"].unique()
        
        if len(con_evidencia) > 0:
            st.markdown("#### 🕵️ Inspección de Evidencia")
            seleccion = st.selectbox(
                "Seleccioná un producto para ver la captura de pantalla:", 
                con_evidencia,
                index=None,
                placeholder="Elegí una infracción 🔴 para ver la prueba..."
            )
            
            if seleccion:
                # Extraemos la fila original para obtener la ruta
                fila_orig = df_radar[df_radar["Producto"] == seleccion].iloc[0]
                ruta_foto = fila_orig["raw_data"].get("screenshot")
                
                if ruta_foto:
                    img_b64 = get_image_base64(ruta_foto) # Usamos tu nueva utilidad
                    if img_b64:
                        st.image(
                            f"data:image/png;base64,{img_b64}", 
                            caption=f"Evidencia de Infracción: {seleccion}",
                            use_container_width=True # Se adapta al ancho de tu ThinkPad
                        )
                    else:
                        st.warning(f"⚠️ El archivo existe en DB pero no se encontró en el disco: {ruta_foto}")
                else:
                    st.info("No hay captura vinculada a este registro.")
        else:
            st.info("✅ No se detectaron infracciones con evidencia fotográfica por el momento.")

        # ==========================================================
        # 3. SELECCIÓN & ANÁLISIS DINÁMICO
        # ==========================================================
        # ==========================================================
        # 3. SELECCIÓN & ANÁLISIS DINÁMICO (RECUPERADO)
        # ==========================================================
        st.divider()
        
        # 1. Agregamos un selector manual por si el clic en la tabla falla
        nombres_productos = [row["Producto"] for row in radar_rows]
        producto_elegido = st.selectbox(
            "🔍 Seleccionar producto para configurar/analizar:", 
            nombres_productos,
            help="Elegí un producto para ver su historial y ajustar los límites de precio."
        )
        
        # 2. Buscamos la fila correspondiente en nuestro DataFrame de radar
        selected_row = next(item for item in radar_rows if item["Producto"] == producto_elegido)
        
        cid = selected_row["full_id"]
        current_keyword = selected_row["Producto"]
        curr_price = float(selected_row["Precio"])
        c_row = selected_row["raw_data"]
            
        # 3. Traemos las reglas actuales de nuestro mapa unificado
        rule = rules_map.get(str(cid)) or {}
        min_p = float(rule.get("min_price_allowed") or 0)
        max_p = float(rule.get("max_price_allowed") or 0)

        st.markdown(f"### 📈 Análisis de Detalle: {current_keyword}")

        # --- MÉTRICAS DE CUMPLIMIENTO ---
        res_hist = supabase.table("price_history").select("checked_at, price").eq("caza_id", cid).order("checked_at").execute()
        df_hist = pd.DataFrame(res_hist.data or [])

        compliance_rate = 100
        if not df_hist.empty and min_p > 0:
            compliance_rate = int((len(df_hist[df_hist["price"] >= min_p]) / len(df_hist)) * 100)

        # --- LÓGICA DE SEMÁFORO MEJORADA ---
        if curr_price <= 0: 
            color, txt = "#808080", "SIN DATOS"
        elif min_p > 0 and curr_price < min_p: 
            color, txt = "#FF4B4B", "🔴 MAP VIOLADO"
        elif max_p > 0 and curr_price > max_p: 
            color, txt = "#FFA500", "🟠 SOBREPRECIO"
        elif min_p == 0 and max_p == 0:
            color, txt = "#555", "⚪ SIN REGLAS"
        else: 
            color, txt = "#28A745", "🟢 CUMPLIMIENTO OK"

        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(f"<small>Precio Actual</small><h3>${int(curr_price):,}</h3>".replace(",", "."), unsafe_allow_html=True)
        with k2: st.markdown(f"<small>Estado</small><h3 style='color:{color}; font-size:18px;'>{txt}</h3>", unsafe_allow_html=True)
        with k3: st.markdown(f"<small>MAP (Mínimo)</small><h3>${int(min_p):,}</h3>".replace(",", "."), unsafe_allow_html=True)
        with k4: st.markdown(f"<small>Compliance</small><h3>{compliance_rate}%</h3>", unsafe_allow_html=True)

        # --- FORMULARIO DE CONFIGURACIÓN ---
        with st.form("config_rules_v2"):
            st.caption(f"⚙️ Ajustar límites para: {current_keyword}")
            c1, c2 = st.columns(2)
            f_min = c1.number_input("MAP (Mínimo permitido)", value=int(min_p), step=1000)
            f_max = c2.number_input("Techo (Máximo permitido)", value=int(max_p), step=1000)

            if st.form_submit_button("💾 Guardar Reglas de Monitoreo", use_container_width=True):
                if not cid:
                    st.error("No se detectó un ID válido.")
                else:
                    # Upsert limpio: borramos y creamos
                    supabase.table("monitor_rules").delete().filter("caza_id", "eq", int(cid)).execute()
                
                    nueva_regla = {
                        "caza_id": int(cid),
                        "user_id": user_id,
                        "min_price_allowed": int(f_min),
                        "max_price_allowed": int(f_max),
                        "product_name": str(current_keyword),
                        "product_url": str(c_row.get("link") or c_row.get("url") or "")
                    }
                
                    res = supabase.table("monitor_rules").insert(nueva_regla).execute()
                    
                    if res.data:
                        st.success(f"✅ ¡Reglas para {current_keyword} actualizadas!")
                        st.rerun()
                    else:
                        st.error("Error al guardar en la base de datos.")

        # --- GRÁFICO HISTÓRICO ---
        if not df_hist.empty:
            df_hist["checked_at"] = pd.to_datetime(df_hist["checked_at"])
            chart = alt.Chart(df_hist).mark_line(point=True, color="#ff4b4b").encode(
                x=alt.X('checked_at:T', title="Fecha de chequeo"),
                y=alt.Y('price:Q', scale=alt.Scale(zero=False), title="Precio ($ ARS)")
            ).properties(height=300)
            
            if min_p > 0:
                rule_line = alt.Chart(pd.DataFrame({'y': [min_p]})).mark_rule(color='red', strokeDash=[5,5]).encode(y='y:Q')
                chart += rule_line
            
            st.altair_chart(chart.interactive(), use_container_width=True)
    else:
        st.info("Esperando datos de los rastreadores...")

            
def render_business_dashboard(plan: str, plan_label_text: str, user_id: str, busquedas: list):
    # Debug en pantalla (activar si querés ver qué valor llega)
    # st.write("DEBUG plan:", plan)
    # st.write("DEBUG busquedas:", busquedas)

    # 🔧 Creamos datos de ejemplo si busquedas está vacío
    if not busquedas:
        busquedas = [
            {"producto": "Notebook Lenovo", "precio": 1200, "currency": "USD"},
            {"producto": "Monitor LG", "precio": 300, "currency": "USD"},
            {"producto": "Mouse Logitech", "precio": 25, "currency": "USD"},
        ]

    # Normalizamos el plan para evitar problemas de mayúsculas/espacios
    plan_normalizado = plan.lower().replace(" ", "_")

    if plan_normalizado == "business_monitor":
        st.subheader("📊 Business Dashboard · Monitor")
        render_business_monitor_dashboard(plan_label_text, user_id, busquedas)

    elif plan_normalizado == "reseller":
        st.subheader("📊 Business Dashboard · Reseller")
        if st.button("Buscar Oportunidades 🚀", use_container_width=True):
            with st.spinner("Olfateando mercado..."):
                ops = obtener_top_oportunidades(user_id)
                if ops:
                    for o in ops:
                        st.success(f"🔥 {o['title']} - {o['price_fmt']}")
                else:
                    st.info("No hay brechas críticas hoy.")

    else:
        st.info("Tu plan no incluye este dashboard.")



# ==========================================================
# SUPABASE HELPERS
# ==========================================================

# ==========================================================
# 📊 DATA HELPERS PARA EL DASHBOARD
# ==========================================================

def get_price_history_series_by_caza(user_id, caza_id):
    """Trae el historial de precios para graficar con Altair"""
    try:
        res = supabase.table("price_history") \
            .select("checked_at, price") \
            .eq("user_id", user_id) \
            .eq("caza_id", caza_id) \
            .order("checked_at", desc=False) \
            .execute()
        
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            df["checked_at"] = pd.to_datetime(df["checked_at"])
            df["price"] = pd.to_numeric(df["price"])
        return df
    except Exception as e:
        print(f"Error en history series: {e}")
        return pd.DataFrame()

def get_price_history_stats_by_caza(user_id, caza_ids):
    """Trae estadísticas rápidas (mín, máx, promedio) para los KPIs"""
    if not caza_ids: return {}
    try:
        res = supabase.table("price_history_stats") \
            .select("*") \
            .eq("user_id", user_id) \
            .in_("caza_id", caza_ids) \
            .execute()
        return {row["caza_id"]: row for row in (res.data or [])}
    except:
        return {}
    
def get_monitor_rules_map(user_id: str, caza_ids: list):
    """Obtiene las reglas de precio configuradas para las cazas del usuario"""
    if not user_id or not caza_ids: return {}
    try:
        res = supabase.table("monitor_rules") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("is_active", True) \
            .in_("caza_id", caza_ids) \
            .execute()
        return {row.get("caza_id"): row for row in (res.data or []) if row.get("caza_id")}
    except:
        return {}

def upsert_monitor_rule(user_id, caza_id, product_name, product_url, source, target_price, min_price_allowed, max_price_allowed):
    """Guarda o actualiza una regla de monitoreo"""
    try:
        payload = {
            "user_id": user_id,
            "caza_id": caza_id,
            "product_name": product_name,
            "product_url": product_url,
            "source": source,
            "target_price": target_price,
            "min_price_allowed": min_price_allowed,
            "max_price_allowed": max_price_allowed,
            "is_active": True
        }
        supabase.table("monitor_rules").upsert(payload).execute()
        return True
    except Exception as e:
        print(f"Error upsert_monitor_rule: {e}")
        return False

def delete_monitor_rule(user_id, caza_id):
    """Desactiva una regla de monitoreo"""
    try:
        supabase.table("monitor_rules") \
            .update({"is_active": False}) \
            .eq("user_id", user_id) \
            .eq("caza_id", caza_id) \
            .execute()
        return True
    except:
        return False
    
def contar_cazas_activas(user_id: str) -> int:
    if not user_id:
        return 0

    for attempt in range(2):
        try:
            res = (
                supabase.table("cazas")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("estado", "activa")
                .execute()
            )
            return int(res.count or 0)
        except Exception as e:
            if attempt == 0:
                time.sleep(0.5)
                continue
            print("[contar_cazas_activas] error:", e)
            return 0


def get_user_profile(user_id: str | None):
    if not user_id:
        return {}

    try:
        res = (
            supabase.table("profiles")
            .select("plan, role, username, email, whatsapp_number")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else {}
    except Exception as e:
        print("[get_user_profile] error:", e)
        return {}


def save_user_whatsapp(user_id: str, whatsapp_number: str) -> bool:
    if not user_id:
        return False

    numero = normalize_phone(whatsapp_number)
    if not numero:
        return False

    try:
        supabase.table("profiles").update(
            {"whatsapp_number": numero}
        ).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print("[save_user_whatsapp] error:", e)
        return False


# ==========================================================
# CAZAS
# ==========================================================
    
def run_manual_hunt(b, headless=True):
    url = b.get("url") or b.get("link") or ""
    kw = b.get("keyword") or b.get("producto") or ""
    precio = b.get("precio_max") or 0
    
    # 🔥 CAMBIO CLAVE: Usamos 'plan_vista' (el del radio button) en vez del plan de la DB
    plan_str = plan_vista.lower() 
    
    # Definimos si es pro/business basándonos en la vista actual
    es_pro_simulado = (plan_str in ["pro", "business_monitor", "business_reseller"])

    # Pasamos el plan y el flag a hunt_offers para que el scraper sepa que debe sacar fotos
    return hunt_offers(url, kw, precio, es_pro=es_pro_simulado, plan=plan_str, headless=headless)
  

def es_plan_business(plan: str) -> bool:
    return normalize_plan_family(plan) in {"business_reseller", "business_monitor"}



def _fmt_money(value):
    try:
        return f"${float(value):,.0f}".replace(",", ".")
    except Exception:
        return "-"


def _fmt_pct(value):
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "-"


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def collect_live_business_ops():
    live_ops = []

    for key, value in st.session_state.items():
        if not str(key).startswith("last_res_"):
            continue

        for r in value or []:
            price = _safe_int(r.get("price") or r.get("precio"), 0)
            if price <= 0:
                continue

            score = float(r.get("_score") or 0)
            title = (r.get("title") or r.get("titulo") or "").strip()
            url = (r.get("url") or r.get("link") or "").strip()
            source = (r.get("source") or "-").strip() or "-"

            if not title:
                continue

            live_ops.append(
                {
                    "title": title,
                    "current_price": price,
                    "opportunity_score": score,
                    "url": url,
                    "source": source,
                }
            )

    uniq = []
    seen = set()
    for op in sorted(
        live_ops,
        key=lambda x: (
            -float(x.get("opportunity_score") or 0),
            _safe_int(x.get("current_price"), 999999999),
        ),
    ):
        key = (
            op.get("title", "").strip().lower(),
            _safe_int(op.get("current_price"), 0),
            op.get("url", "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        uniq.append(op)

    return uniq


def get_price_history_stats_by_caza(user_id: str, caza_ids: list):
    caza_ids = [x for x in caza_ids if x is not None]
    if not user_id or not caza_ids:
        return {}

    try:
        res = (
            supabase.table("price_history")
            .select("caza_id, price, checked_at, title, url, source")
            .eq("user_id", user_id)
            .in_("caza_id", caza_ids)
            .order("checked_at", desc=True)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        print("[get_price_history_stats_by_caza] error:", e)
        return {}

    stats = {}

    for row in rows:
        caza_id = row.get("caza_id")
        if caza_id is None:
            continue

        price = _safe_int(row.get("price"), 0)
        if price <= 0:
            continue

        if caza_id not in stats:
            stats[caza_id] = {
                "prices": [],
                "latest_price": price,
                "latest_checked_at": row.get("checked_at"),
                "title": row.get("title") or "",
                "url": row.get("url") or "",
                "source": row.get("source") or "",
            }

        stats[caza_id]["prices"].append(price)

    for caza_id, item in stats.items():
        prices = item.pop("prices", [])
        if not prices:
            continue

        item["min_price"] = min(prices)
        item["max_price"] = max(prices)
        item["avg_price"] = sum(prices) / len(prices)
        item["samples"] = len(prices)

    return stats


def get_price_history_series_by_caza(user_id: str, caza_id):
    if not user_id or caza_id is None:
        return pd.DataFrame()

    try:
        res = (
            supabase.table("price_history")
            .select("checked_at, price")
            .eq("user_id", user_id)
            .eq("caza_id", caza_id)
            .order("checked_at", desc=False)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        print("[get_price_history_series_by_caza] error:", e)
        return pd.DataFrame()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "checked_at" in df.columns:
        df["checked_at"] = pd.to_datetime(df["checked_at"], errors="coerce")
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["checked_at", "price"]).sort_values("checked_at")
    return df


def get_monitor_rules_map(user_id: str, caza_ids: list):
    caza_ids = [x for x in caza_ids if x is not None]
    if not user_id or not caza_ids:
        return {}

    try:
        res = (
            supabase.table("monitor_rules")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .in_("caza_id", caza_ids)
            .execute()
        )
        rows = res.data or []
        return {row.get("caza_id"): row for row in rows if row.get("caza_id") is not None}
    except Exception as e:
        print("[get_monitor_rules_map] error:", e)
        return {}


def upsert_monitor_rule(
    user_id: str,
    caza_id,
    product_name: str,
    product_url: str,
    source: str,
    target_price,
    min_price_allowed,
    max_price_allowed,
) -> bool:
    try:
        if not user_id:
            st.error("❌ No se detectó un usuario válido para guardar la regla.")
            return False

        if caza_id is None:
            st.error("❌ Elegí una caza/publicación antes de guardar la regla.")
            return False

        target_i = parse_price_to_int(target_price)
        min_i = parse_price_to_int(min_price_allowed)
        max_i = parse_price_to_int(max_price_allowed)

        if min_i > 0 and max_i > 0 and min_i > max_i:
            st.error("❌ El precio mínimo permitido no puede ser mayor que el máximo permitido.")
            return False

        payload = {
            "user_id": user_id,
            "caza_id": caza_id,
            "product_name": (product_name or "").strip(),
            "product_url": (product_url or "").strip(),
            "source": (source or "generic").strip().lower(),
            "target_price": target_i,
            "min_price_allowed": min_i,
            "max_price_allowed": max_i,
            "is_active": True,
        }

        existing = (
            supabase.table("monitor_rules")
            .select("id")
            .eq("user_id", user_id)
            .eq("caza_id", caza_id)
            .limit(1)
            .execute()
        )
        rows = existing.data or []

        if rows:
            rid = rows[0]["id"]
            supabase.table("monitor_rules").update(payload).eq("id", rid).execute()
        else:
            supabase.table("monitor_rules").insert(payload).execute()

        return True
    except Exception as e:
        st.error(f"❌ Error real monitor: {e}")
        print("[upsert_monitor_rule] error:", e)
        return False


def delete_monitor_rule(user_id: str, caza_id) -> bool:
    try:
        if not user_id or caza_id is None:
            return False

        res = (
            supabase.table("monitor_rules")
            .update({"is_active": False})
            .eq("user_id", user_id)
            .eq("caza_id", caza_id)
            .execute()
        )
        return True if getattr(res, "data", None) is not None else True
    except Exception as e:
        print("[delete_monitor_rule] error:", e)
        return False


def monitor_status(current_price, min_allowed, max_allowed):
    price = _safe_int(current_price, 0)
    min_p = _safe_int(min_allowed, 0)
    max_p = _safe_int(max_allowed, 0)

    if price <= 0:
        return "⚪ Sin precio"

    if min_p > 0 and price < min_p:
        return "🔻 Debajo del mínimo"

    if max_p > 0 and price > max_p:
        return "🔺 Encima del máximo"

    # zona amarilla: dentro de ±5% del límite configurado
    if min_p > 0 and price <= int(min_p * 1.05):
        return "🟡 Cerca del mínimo"
    if max_p > 0 and price >= int(max_p * 0.95):
        return "🟡 Cerca del máximo"

    if min_p > 0 or max_p > 0:
        return "✅ En rango"

    return "⚪ Sin rango"


def compliance_pct_from_series(df: pd.DataFrame, min_allowed, max_allowed):
    if df is None or df.empty:
        return None

    min_p = _safe_int(min_allowed, 0)
    max_p = _safe_int(max_allowed, 0)

    if min_p <= 0 and max_p <= 0:
        return None

    series = df["price"].dropna().astype(float)
    if series.empty:
        return None

    in_range = pd.Series([True] * len(series), index=series.index)
    if min_p > 0:
        in_range &= series >= min_p
    if max_p > 0:
        in_range &= series <= max_p

    return round(float(in_range.mean() * 100), 1)


def _make_histogram_df(series: pd.Series, bins: int = 8):
    if series is None or series.empty:
        return pd.DataFrame()
    try:
        cuts = pd.cut(series, bins=min(bins, max(2, series.nunique())), duplicates="drop")
        hist = cuts.value_counts().sort_index()
        labels = [f"{int(interval.left):,}-{int(interval.right):,}".replace(",", ".") for interval in hist.index]
        return pd.DataFrame({"rango": labels, "cantidad": hist.values}).set_index("rango")
    except Exception:
        return pd.DataFrame()


def render_business_reseller_dashboard(plan_label_text: str):
    st.subheader("📊 Business Dashboard · Reseller")
    st.caption("Detectá oportunidades inmediatas y priorizá las mejores presas para comprar o revender.")

    oportunidades_db = obtener_top_oportunidades(limit=20) or []
    live_ops = collect_live_business_ops()

    total_ops = len(oportunidades_db) + len(live_ops)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Oportunidades", total_ops)
    with c2:
        st.metric("Históricas", len(oportunidades_db))
    with c3:
        st.metric("En vivo", len(live_ops))

    st.markdown("### ⚡ Mejores oportunidades ahora")

    if not live_ops:
        st.info("Todavía no hay oportunidades en vivo. Probá olfatear tus cazas para alimentar este panel.")
    else:
            for i, op in enumerate(live_ops[:15]):
                precio_act = int(op.get("current_price") or 0)
                
                # MVP: Simulamos que el revendedor le aplica un 40% de remarco al precio mínimo histórico.
                # Más adelante, esto lo sacamos de la tabla de reglas del usuario.
                precio_min = precio_act # Por ahora usamos el actual si no hay data cruzada
                precio_reventa_estimado = int(precio_act * 1.40) 
                
                mostrar_tarjeta_oportunidad(
                    id_rastreo=f"live_{i}",
                    titulo=op.get("title") or "Sin título",
                    precio_actual=_fmt_money(precio_act),
                    precio_min_historico=_fmt_money(precio_min),
                    precio_reventa_usuario=_fmt_money(precio_reventa_estimado)
                )

    st.markdown("### 🏆 Ranking histórico de oportunidades")
    if not oportunidades_db:
        st.info("Todavía no hay oportunidades históricas guardadas.")
    else:
        rows = []
        for op in oportunidades_db:
            rows.append(
                {
                    "Score": round(float(op.get("opportunity_score") or 0), 2),
                    "Producto": op.get("title") or op.get("product_id") or "Sin título",
                    "Fuente": (op.get("source") or "-").strip() or "-",
                    "Precio actual": _fmt_money(op.get("current_price")),
                    "Mínimo histórico": _fmt_money(op.get("historic_min_price")),
                    "Diff vs mín": _fmt_pct(op.get("diff_vs_min")),
                    "Link": op.get("url") or "",
                }
            )

        st.dataframe(rows, use_container_width=True, hide_index=True)



# ==========================================================
# CSS
# ==========================================================

st.markdown(
    """
    <style>

    .main .block-container {
        max-width: 980px;
        padding-top: 1.1rem;
        padding-bottom: 2rem;
    }

    .auth-form-shell {
        max-width: 560px;
        margin: 0 auto;
        padding: 0.25rem 0 0.75rem 0;
    }

    .plans-shell {
        max-width: 980px;
        margin: 0 auto;
        padding: 0.35rem 0 1rem 0;
    }

    .plans-title {
        text-align: center;
        margin-bottom: 1rem;
    }

    /* --- MODIFICACIÓN DE CARDS --- */
    .oh-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        
        /* Esto hace que todas midan lo mismo */
        min-height: 380px; 
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        
        transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
    }

    .oh-card:hover {
        transform: translateY(-8px);
        border-color: #ff4b4b; /* Color que combina con tus botones */
        box-shadow: 0 20px 40px rgba(0,0,0,0.4);
        background: rgba(255,255,255,0.07);
    }

    .oh-card h3 {
        margin-top: 0;
        margin-bottom: 0.8rem;
        font-size: 1.4rem;
        color: #ffffff;
    }

    .oh-card p {
        opacity: 0.9;
        line-height: 1.6;
        margin-bottom: 0.8rem;
        font-size: 0.95rem;
    }

    .oh-badge {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 6px 12px;
        border-radius: 999px;
        background: linear-gradient(90deg, #333, #444);
        color: #eee;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    /* ---------------------------- */

    div[data-baseweb="tab-list"] {
        gap: 10px;
    }

    button[data-baseweb="tab"] {
        border-radius: 14px !important;
        padding: 10px 18px !important;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        border-radius: 14px !important;
    }

    .stButton > button {
        border-radius: 14px !important;
    }

    button[kind="primary"] {
        background: linear-gradient(90deg,#ff4b4b,#ff6b6b);
        border: none !important;
    }

    .auth-form-shell .stAlert {
        margin-bottom: 1rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================================
# AUTH UI HELPERS
# ==========================================================

def mostrar_selector_producto():
    st.markdown('<div class="plans-shell">', unsafe_allow_html=True)
    st.markdown('<h3 class="plans-title">Elegí tu versión</h3>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown(
            """
            <div class="oh-card">
                <span class="oh-badge">Uso personal</span>
                <h3>Howlify</h3>
                <p><b>✈️ Tu radar de Vuelos, Hoteles y Airbnb.</b></p>
                <p>Encontrá pasajes baratos, paquetes y productos de uso diario al mejor precio. Configurá tu cacería y recibí alertas automáticas cuando bajan.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Elegir Howlify", use_container_width=True, key="choose_consumer"):
            st.session_state["product_type"] = "consumer"
            st.rerun()

    with c2:
        st.markdown(
            """
            <div class="oh-card">
                <span class="oh-badge">Negocio</span>
                <h3>Howlify Business</h3>
                <p><b>🎯 Price Intelligence & Control de Mercado.</b></p>
                <p>Monitoreo profesional de rangos de precio, detección de oportunidades de reventa y reportes diarios programados para tu empresa.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Elegir Business", use_container_width=True, key="choose_business"):
            st.session_state["product_type"] = "business"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def mostrar_planes_consumer():
    st.markdown('<div class="plans-shell">', unsafe_allow_html=True)
    st.markdown('<h3 class="plans-title">Elegí tu plan Howlify</h3>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown(
            """
            <div class="oh-card">
                <span class="oh-badge">Entrada</span>
                <h3>Starter</h3>
                <p><strong>USD 9 / mes</strong></p>
                <p>✅ 5 productos en radar<br>
                ✅ <b>🛒 ML + Tiendas generales</b><br>
                ✅ Ideal para compras diarias<br>
                ✅ Alertas por email</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Elegir Starter", use_container_width=True, key="choose_starter"):
            st.session_state["plan_elegido"] = "starter"
            st.rerun()

    with c2:
        st.markdown(
            """
            <div class="oh-card">
                <span class="oh-badge">Más elegido</span>
                <h3>Pro</h3>
                <p><strong>USD 15 / mes</strong></p>
                <p>✅ 15 productos en radar<br>
                ✅ <b>✈️ Especialista en Viajes (Airbnb + Despegar)</b><br>
                ✅ ⚡ Monitoreo cada 15 min<br>
                ✅ Alertas por WhatsApp</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Elegir Pro", use_container_width=True, key="choose_pro"):
            st.session_state["plan_elegido"] = "pro"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def mostrar_planes_business():
    st.markdown('<div class="plans-shell">', unsafe_allow_html=True)
    st.markdown('<h3 class="plans-title">Elegí tu plan Howlify Business</h3>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown(
            """
            <div class="oh-card">
                <span class="oh-badge">Reventa</span>
                <h3>Business Reseller</h3>
                <p><strong>USD 39 / mes</strong></p>
                <p>✅ <b>🚀 Detección de Oportunidades</b><br>
                ✅ Alertas de stock y quiebre de precio<br>
                ✅ Historial para análisis de margen<br>
                ✅ 📲 Alertas prioritarias (WhatsApp/Telegram)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Elegir Business Reseller", use_container_width=True, key="choose_business_reseller"):
            st.session_state["plan_elegido"] = "business_reseller"
            st.rerun()

    with c2:
        st.markdown(
            """
            <div class="oh-card">
                <span class="oh-badge">Monitoreo</span>
                <h3>Business Monitor</h3>
                <p><strong>USD 79 / mes</strong></p>
                <p>✅ <b>🎯 Price Intelligence 24/7</b><br>
                ✅ Control de rangos y variaciones<br>
                ✅ 📊 Reportes programados (Días/Horas)<br>
                ✅ 📲 WhatsApp Premium</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Elegir Business Monitor", use_container_width=True, key="choose_business_monitor"):
            st.session_state["plan_elegido"] = "business_monitor"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================================
# PASSWORD RECOVERY
# ==========================================================

if not st.query_params.get("access_token"):
    components.html(
        """
        <script>
        const hash = window.parent.location.hash;
        if (hash && hash.length > 1) {
            const qs = hash.substring(1);
            const newUrl = window.parent.location.origin + window.parent.location.pathname + "?" + qs;
            window.parent.location.replace(newUrl);
        }
        </script>
        """,
        height=0,
    )

params = st.query_params
access_token = params.get("access_token", None)
refresh_token = params.get("refresh_token", None)
type_param = params.get("type", None)

if access_token:
    st.title("🔑 Restablecer contraseña")
    new_pass = st.text_input("Nueva contraseña", type="password")
    new_pass2 = st.text_input("Repetir nueva contraseña", type="password")

    if st.button("Guardar nueva contraseña"):
        if not new_pass or len(new_pass) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres.")
            st.stop()
        if new_pass != new_pass2:
            st.error("Las contraseñas no coinciden.")
            st.stop()
        try:
            supabase.auth.set_session(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token or "",
                }
            )
            supabase.auth.update_user({"password": new_pass})
            st.success("✅ Contraseña actualizada. Ya podés iniciar sesión.")
            st.stop()
        except Exception as e:
            st.error(f"Error actualizando contraseña: {e}")
            st.stop()

# ==========================================================
# LOGO RENDER
# ==========================================================
def render_logo(logo_b64: str):
    html = f"""
    <div style="display:flex; justify-content:center; margin-top:10px; margin-bottom:25px;">
        <div style="
            width:210px;
            height:210px;
            border-radius:50%;
            overflow:hidden;
            display:flex;
            align-items:center;
            justify-content:center;
            background: radial-gradient(circle at center, #ffffff 58%, #e6edf5 100%);
            box-shadow: inset 0 0 45px rgba(0,0,0,0.50),
                        inset 0 0 150px rgba(0,0,0,0.30),
                        0 0 35px rgba(120,180,255,0.40),
                        0 0 90px rgba(120,180,255,0.25),
                        0 0 160px rgba(120,180,255,0.12),
                        0 0 220px rgba(120,180,255,0.06);">
            <img src="data:image/png;base64,{logo_b64}"
                 style="width:100%; height:100%; object-fit:cover; display:block; transform:scale(1.03);" />
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
# ==========================================================
# AUTH
# ==========================================================
if "user_logged" not in st.session_state:
    logo_b64 = get_base64_logo(LOGO_PATH)
    render_logo(logo_b64)

    t1, t2 = st.tabs(["🔐 Iniciar Sesión", "🐾 Unirse a la Jauría"])

    with t1:
        st.markdown('<div class="auth-form-shell">', unsafe_allow_html=True)
        st.markdown("### Iniciar sesión")

        u = st.text_input("Usuario o Email", key="l_u")
        p = st.text_input("Contraseña", type="password", key="l_p")

        if st.button("Entrar", use_container_width=True, type="primary", key="l_submit"):
            user, err = supa_login(u, p)
            if user:
                st.session_state["user_logged"] = user
                
                # Cargamos perfil para la sesión
                profile = {}
                try:
                    res = (
                        supabase.table("profiles")
                        .select("plan, role, username, email, whatsapp_number")
                        .eq("user_id", user.id)
                        .limit(1)
                        .execute()
                    )
                    profile = res.data[0] if res.data else {}
                except Exception as e:
                    print("[login profile] error:", e)

                st.session_state["profile"] = profile
                st.rerun()
            else:
                st.error(err) # El error ya viene "cheto" desde auth_supabase.py

        if st.button("Olvidé mi contraseña", use_container_width=True, key="l_reset"):
            if "@" in (u or ""):
                # Ahora devuelve (bool, mensaje)
                ok, msg = supa_reset_password(u)
                if ok: st.success(msg)
                else: st.error(msg)
            else:
                st.warning("⚠️ Ingresá tu EMAIL en el campo de arriba para restablecer.")

        st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        if st.session_state["product_type"] is None:
            mostrar_selector_producto()

        elif st.session_state["plan_elegido"] is None:
            if st.session_state["product_type"] == "consumer":
                mostrar_planes_consumer()
            elif st.session_state["product_type"] == "business":
                mostrar_planes_business()

            c1, c2, c3 = st.columns([1, 1.2, 1])
            with c2:
                if st.button("← Volver", use_container_width=True, key="back_product_type"):
                    st.session_state["product_type"] = None
                    st.rerun()

        else:
            st.markdown('<div class="auth-form-shell">', unsafe_allow_html=True)
            st.markdown("### Crear cuenta")

            plan = st.session_state["plan_elegido"]
            st.info(f"Registrando nuevo miembro · Plan {plan_label(plan)}")

            nu = st.text_input("Usuario", key="r_user", placeholder="Ej: Lobo_De_Cuyo")
            em = st.text_input("Email", key="r_email", placeholder="tu@email.com")
            
            # --- SECCIÓN DE PASSWORDS ---
            np = st.text_input("Elegí tu Contraseña", type="password", key="r_pass")
            np_confirm = st.text_input("Repetí la Contraseña", type="password", key="r_pass_confirm")

            if np:
                level, icon = password_strength(np)
                st.caption(f"Seguridad: {icon} {level}")

            if st.button("Finalizar Registro", use_container_width=True, key="r_submit", type="primary"):
                # Validamos que no falte nada antes de llamar a la función
                if not nu or not em or not np or not np_confirm:
                    st.warning("⚠️ No te olvides de completar todos los campos.")
                else:
                    # LLAMADA A LA FUNCIÓN CON 5 PARÁMETROS
                    user, err = supa_signup(em, np, np_confirm, nu, plan)
                    
                    if user and not err:
                        st.balloons()
                        st.success("🔥 ¡Cuenta creada! Revisá tu mail para confirmar la suscripción.")
                        st.info("Una vez confirmado, ya podés iniciar sesión en la pestaña de al lado.")
                    elif err:
                        st.error(err) # Acá sale el mensaje en criollo (ya registrado, etc)

            if st.button("← Cambiar plan", use_container_width=True, key="back_to_plans"):
                st.session_state["plan_elegido"] = None
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# ==========================================================
# MAIN
# ==========================================================
# 1. Cargamos el usuario de la sesión
user = st.session_state["user_logged"]
email = (getattr(user, "email", None) or "").strip()
user_id = getattr(user, "id", None)

if not user_id:
    st.session_state.pop("user_logged", None)
    st.warning("⚠ Tu sesión no es válida. Volvé a iniciar sesión.")
    st.rerun()

# 2. Cargamos el perfil
profile = st.session_state.get("profile") or get_user_profile(user_id)

# 3. Seguimos con el resto de tus variables originales
plan_real_raw = (profile.get("plan") or "starter").strip().lower()
plan_real = normalize_plan_family(plan_real_raw)
role = (profile.get("role") or "user").strip().lower()
nick = (profile.get("username") or "").strip()

display_name = nick if nick else (email.split("@")[0] if "@" in email else "usuario")
es_admin = role == "admin"

if DEBUG:
    st.sidebar.write("DEBUG session email:", email)
    st.sidebar.write("DEBUG session user_id:", user_id)
    st.sidebar.write("DEBUG profile raw:", profile)
    st.sidebar.write("DEBUG role:", role)
    st.sidebar.write("DEBUG es_admin:", es_admin)
    st.sidebar.write("DEBUG plan_real_raw:", plan_real_raw)
    st.sidebar.write("DEBUG plan_real:", plan_real)

if es_admin:
    plan_vista = "admin"
else:
    plan_vista = plan_real

# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.markdown("### 📌 Menú Principal")
    
    # Averiguamos si tiene plan business para armar el menú
    _tmp_rules = get_effective_plan_rules(plan_vista)
    _has_biz = _tmp_rules["features"].get("business_mode", False)
    
    opciones_menu = ["🐺 Mis Rastreadores", "👤 Mi Perfil"]

    # st.write("DEBUG plan_real:", plan_real)
    # st.write("DEBUG _has_biz:", _has_biz)

    
    # Forzamos el botón si sos admin o si tenés el plan business
    if _has_biz or "admin" in plan_real.lower() or "business" in plan_real.lower():
        opciones_menu.insert(1, "📊 Dashboard Business")
        
    # El menú de navegación reina acá arriba
    vista_actual = st.radio("Navegación", opciones_menu, label_visibility="collapsed")
    
    st.divider()

    st.markdown("### ⚙️ Utilidades")
    st.session_state["sound_enabled"] = st.checkbox("🔊 Sonido", value=st.session_state["sound_enabled"])

    if st.button("🧩 Conectar MercadoLibre (resolver captcha/login)", use_container_width=True):
        try:
            proc = subprocess.run(
                [sys.executable, "scripts/ml_connect.py"],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                st.success("✅ Sesión de MercadoLibre guardada/actualizada.")
            else:
                st.error("❌ No se pudo guardar la sesión de MercadoLibre.")
            if (proc.stdout or "").strip():
                st.code(proc.stdout.strip())
            if (proc.stderr or "").strip():
                st.code(proc.stderr.strip())
        except Exception as e:
            st.error(f"Error ejecutando ml_connect.py: {e}")

    st.divider()
    st.subheader("👤 Sesión")
    st.caption(f"Usuario: `{display_name}`")
    st.caption(f"Plan real: **{plan_label(plan_real)}**")

    if es_admin:
        st.divider()
        st.subheader("🛠️ Panel de Admin")

        if st.button("🔄 Refrescar panel", use_container_width=True):
            st.rerun()

        plan_simulado = st.radio(
            "Simular vista de plan:",
            ["Starter", "Pro", "Business Reseller", "Business Monitor"],
            index=(
                0 if plan_real == "starter"
                else 1 if plan_real == "pro"
                else 2 if plan_real == "business_reseller"
                else 3
            ),
            key="admin_plan_sim",
        )
        plan_sim_map = {
            "starter": "starter",
            "pro": "pro",
            "business reseller": "business_reseller",
            "business monitor": "business_monitor",
        }
        plan_vista = plan_sim_map.get(plan_simulado.lower(), plan_real)
        st.info(f"Viendo como: {plan_simulado}")

        st.caption("Esta simulación cambia límites y UI, no cambia de usuario ni de dataset.")

        st.divider()
        st.subheader("👥 Usuarios (últimos 30)")
        try:
            res = (
                supabase.table("profiles")
                .select("user_id, username, email, plan, role, created_at, whatsapp_number")
                .order("created_at", desc=True)
                .limit(30)
                .execute()
            )
            rows = res.data or []
            if not rows:
                st.caption("No hay usuarios.")
            else:
                st.dataframe(rows, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error cargando usuarios: {e}")


# ==========================================================
# PLAN / BUSQUEDAS
# ==========================================================

plan = plan_vista
rules = get_effective_plan_rules(plan)



st.session_state["busquedas"] = obtener_cazas(user_id, plan_real_raw)


# ==========================================================
# 🎯 RENDER CENTRAL (EL MURO DE BERLÍN)
# ==========================================================
#print("DEBUG vista_actual:", vista_actual)   # 👈 esto en la consola
#st.write("Vista actual:", vista_actual)      # 👈 esto en la interfaz web

if vista_actual == "📊 Dashboard Business":
    
    render_business_dashboard(plan_real_raw, rules['label'], user_id, st.session_state["busquedas"])
    render_footer()
    st.stop()  # 🛑 ESTO ES LO MÁS IMPORTANTE

if vista_actual == "👤 Mi Perfil":
    render_profile_section(email, rules['label'])
    render_footer()
    st.stop()

st.title(f"Panel de {display_name} · Plan {rules['label']}")


limite_plan = int(rules["max_cazas_activas"])
cazas_activas = contar_cazas_activas(user_id)
restantes = limite_plan - cazas_activas

col1, col2 = st.columns(2)
with col1:
    st.info(f"📦 Estás usando {cazas_activas} de {limite_plan} cazas disponibles.")
with col2:
    if restantes > 0:
        st.success(f"✅ Te quedan {restantes} disponibles.")
    else:
        st.warning("⚠️ Has alcanzado el límite de tu plan.")
st.caption(
    f"Notificaciones disponibles: {', '.join(rules['notifications']).upper()} · "
    f"Frecuencia mínima: {rules['min_interval_minutes']} min"
)

st.divider()

# ==========================================================
# 0. LÓGICA DE IDENTIDAD (CORREGIDA PARA SIMULACIÓN)
# ==========================================================
# Si sos admin, usamos el plan que elegiste en el radio button 'admin_plan_sim'
# Si no, usamos el plan real de tu base de datos.
if es_admin:
    # 'admin_plan_sim' es la key del radio button en tu sidebar
    plan_simulado_raw = st.session_state.get('admin_plan_sim', 'Starter')
    # Mapeamos el nombre lindo del radio button al nombre técnico de la DB
    mapa_tecnico = {
        "Starter": "starter",
        "Pro": "pro",
        "Business Reseller": "business_reseller",
        "Business Monitor": "business_monitor"
    }
    plan_para_el_form = mapa_tecnico.get(plan_simulado_raw, "starter")
else:
    plan_para_el_form = plan_real_raw

familia_raw = normalize_plan_family(plan_para_el_form)
es_solo_monitor = (plan_para_el_form == "business_monitor")


# ==========================================================
# 1. ZONA DE CONFIGURACIÓN (UNIFICADA)
# ==========================================================
# --- 📲 EXPANDER DE NOTIFICACIONES (RESTAURADO E INTEGRADO) ---
with st.expander("📲 Configurar Notificaciones", expanded=False):
    st.markdown("Gestioná tus canales de alerta para no perder ninguna presa.")
    
    # 1. Carga de datos de perfil
    try:
        res_prof = supabase.table("profiles").select("telegram_id", "whatsapp_number", "email_notifications").eq("user_id", user_id).execute()
        prof_data = res_prof.data[0] if res_prof.data else {}
        t_id = prof_data.get("telegram_id")
        ws_actual = prof_data.get("whatsapp_number")
        mail_active = prof_data.get("email_notifications", True)
    except Exception as e_prof:
        st.error(f"Error al cargar perfil: {e_prof}")
        t_id, ws_actual, mail_active = None, None, True

    # Traemos las reglas del plan para validar permisos
    rules = get_effective_plan_rules(plan)
    # Usamos las variables que ya tenés en tu lógica para planes
    # (Ajustalas si tus llaves de rules se llaman distinto, ej: rules['can_use_telegram'])
    
    # --- 📧 SECCIÓN EMAIL (Para todos los planes) ---
    st.markdown("#### 📧 Correo Electrónico")
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        st.info(f"Las alertas se enviarán a: **{st.session_state.get('user_email', 'tu email de registro')}**")
    with col_m2:
        nuevo_estado_mail = st.toggle("Activar", value=mail_active, key="tg_mail_notif")
        
    if nuevo_estado_mail != mail_active:
        supabase.table("profiles").update({"email_notifications": nuevo_estado_mail}).eq("user_id", user_id).execute()
        st.toast("Preferencia de Email actualizada")

    st.divider()

    # --- 🟦 SECCIÓN TELEGRAM (Solo Pro y Business) ---
    st.markdown("#### 🟦 Telegram")
    # Verificamos si el plan permite Telegram (Pro o Business)
    if "pro" in plan.lower() or "business" in plan.lower():
        if not t_id:
            url_bot = f"https://t.me/howlify_bot?start={user_id}" 
            st.link_button("🐺 Vincular Telegram ahora", url_bot, width="stretch")
            if st.button("🔄 Verificar Vinculación", key="btn_verify_tg_vfinal"): 
                st.rerun()
        else:
            st.success(f"✅ Vinculado (ID: {t_id})")
            col_tel1, col_tel2 = st.columns(2)
            with col_tel1:
                if st.button("🧪 Probar Alerta", width="stretch", key="btn_test_tg_vfinal"): 
                    with st.spinner("Enviando..."):
                        exito = enviar_telegram(t_id, "¡Aullido de prueba exitoso! 🐺")
                        if exito: st.toast("✅ ¡Mensaje enviado!")
                        else: st.error("❌ Falló el envío.")
            with col_tel2:
                if st.button("🗑️ Desvincular", width="stretch", key="btn_unlink_tg"):
                    supabase.table("profiles").update({"telegram_id": None}).eq("user_id", user_id).execute()
                    st.warning("Cuenta desvinculada.")
                    time.sleep(1); st.rerun()
    else:
        st.warning("🔒 Telegram disponible en planes **Pro** y **Business**.")

    st.divider()

    # --- 🟩 SECCIÓN WHATSAPP (Solo Business) ---
    st.markdown("#### 🟩 WhatsApp")
    # Según tu lógica anterior, solo para Business
    if "business" in plan.lower():
        ws_num = st.text_input("Número (ej: 54911...)", value=ws_actual if ws_actual else "", key="ws_input_vfinal")
        if st.button("💾 Guardar WhatsApp", width="stretch", key="btn_save_ws_vfinal"):
            if ws_num.strip():
                supabase.table("profiles").update({"whatsapp_number": ws_num.strip()}).eq("user_id", user_id).execute()
                st.success("✅ Guardado.")
                time.sleep(1); st.rerun()
    else:
        st.warning("🔒 WhatsApp solo disponible en plan **Business Monitor**.")

# --- ➕ NUEVA CACERÍA ---
total_ocupado = cazas_activas
if total_ocupado < limite_plan:
    with st.expander("➕ Configurar nueva cacería", expanded=False):
        n_url = st.text_input("URL", placeholder="Pegá el link de Mercado Libre...", key="new_hunt_url_final")
        n_key = st.text_input("Palabra clave", placeholder="Ej: Lavarropas Inverter...", key="new_hunt_key_final")

        if es_solo_monitor:
            # --- VISTA MONITOR (MAP) ---
            st.markdown("##### 🛡️ Configuración de Monitoreo MAP")
            c_min, c_max = st.columns(2)
            with c_min:
                n_min = st.number_input("Mínimo permitido (MAP)", value=0, step=1000, key="n_min_biz_final")
            with c_max:
                n_max = st.number_input("Techo máximo", value=0, step=1000, key="n_max_biz_final")
            tipo_db, n_price = "piso", n_min 
            
            st.markdown("##### 🔔 Alertas inmediatas")
            col_n = st.columns(3)
            alerta_tg = col_n[0].checkbox("Telegram", value=True, key="chk_tg_biz")
            alerta_wa = col_n[1].checkbox("WhatsApp", value=False, key="chk_wa_biz")
            alerta_em = col_n[2].checkbox("Email", value=True, key="chk_em_biz")
        else:
            # --- VISTA ESTÁNDAR (STARTER, PRO, RESELLER) ---
            st.markdown("##### 🎯 Configuración de Cacería")
            tipo_alerta_ui = st.radio("Estrategia:", ["Precio Piso", "Descuento %"], horizontal=True, key="strat_radio_final")
            if tipo_alerta_ui == "Precio Piso":
                n_price = st.number_input("Precio Máximo ($)", min_value=0, value=500000, step=1000, key="price_piso_final")
                tipo_db = "piso"
            else:
                n_price = st.slider("Porcentaje deseado (%)", 5, 90, 35, key="price_desc_final")
                tipo_db = "descuento"
            n_min, n_max = 0, 0 

        # ==========================================================
        # 🐺 SECCIÓN DE FRECUENCIA Y REPORTE DIARIO
        # ==========================================================
        st.divider()
        
        # 1. FRECUENCIA DE RASTREO (Para todos los planes)
        n_freq = st.selectbox("Frecuencia de rastreo del Sabueso:", rules["freq_options"], key="freq_sel_final")

        # 2. CONFIGURACIÓN DE REPORTE (Solo Business Monitor y Reseller)
        # Usamos familia_raw que ya definimos arriba del bloque
        if "business" in familia_raw.lower():
            st.markdown("#### 📅 Configuración de Reporte de Salud")
            st.caption("Recibí un resumen del estado de tus links y alertas en tu horario preferido.")
            
            c_dias, c_hora = st.columns([2, 1])
            with c_dias:
                dias_rep = st.multiselect(
                    "Días de envío:",
                    ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
                    default=["Lunes", "Miércoles", "Viernes"],
                    key="dias_rep_new_caza"
                )
            with c_hora:
                hora_rep = st.selectbox(
                    "Hora:",
                    [f"{h:02d}:00" for h in range(24)],
                    index=9, # 09:00 AM por defecto
                    key="hora_rep_new_caza"
                )
        else:
            # Para Starter/Pro seteamos valores vacíos para no romper la función de guardado
            dias_rep, hora_rep = [], None

        # ==========================================================
        # BOTÓN LANZAR
        # ==========================================================
        if st.button("Lanzar", width="stretch", key="btn_lanzar_caza_final"):
            if not n_url.strip() or not n_key.strip():
                st.error("Completá URL y Palabra clave.")
            else:
                url_limpia = clean_ml_url(n_url)
                precio_max_int = parse_price_to_int(n_price)
                src = infer_source_from_url(url_limpia) or DEFAULT_SOURCE
                
                # 🐺 NOTA: Aquí deberás actualizar guardar_caza_supabase 
                # para que acepte dias_rep y hora_rep más adelante.
                res = guardar_caza_supabase(user_id, n_key, url_limpia, precio_max_int, n_freq, tipo_db, plan, src, dias_rep=dias_rep, hora_rep=hora_rep)
                
                if res is True:
                    if es_solo_monitor:
                        res_caza = supabase.table("cazas").select("id").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
                        if res_caza.data:
                            upsert_monitor_rule(user_id, res_caza.data[0]["id"], n_key, url_limpia, src, n_min, n_min, n_max)
                    
                    st.success("✅ Caza creada correctamente.")
                    time.sleep(1); st.rerun()

st.divider() # Mantiene la separación con el listado de abajo

# ==========================================================
# 2. BOTÓN MASIVO Y LISTADO (CENTRO DE CONTROL)
# ==========================================================
status_slot = st.empty() 
progreso_bar_slot = st.empty()
card_placeholders = {}

if st.session_state.get("busquedas"):
    col_t, col_b = st.columns([2, 1])
    with col_t:
        st.subheader(f"🎯 Mis Cacerías ({rules.get('label', 'Monitor')})")
    with col_b:
        if st.button("🔎 Olfatear todas", width="stretch", type="primary", key="btn_massive_hunt_vfinal"):
            busquedas = st.session_state["busquedas"]
            encontro_total = False
            bar = progreso_bar_slot.progress(0)
            for i, b in enumerate(busquedas):
                rid = str(b.get("id", i))
                bar.progress((i + 1) / len(busquedas))
                if rid in card_placeholders: card_placeholders[rid].warning("⏳ Olfateando...")
                try:
                    resultados = run_manual_hunt(b, headless=FORCE_HEADLESS) or []
                    st.session_state[f"last_res_{rid}"] = resultados
                    if resultados: 
                        encontro_total = True
                        save_price_history(user_id, b.get("id"), resultados)
                except: continue
            if encontro_total and st.session_state.get("sound_enabled", True):
                st.session_state["play_sound"] = True
            bar.empty(); st.rerun()

    for i, b in enumerate(st.session_state["busquedas"]):
        rid = str(b.get("id", i))
        kw = (b.get("producto") or b.get("keyword") or "Sin nombre").upper()
        url = b.get("link") or b.get("url") or ""
        p_max = b.get("precio_max", 0)

        with st.container(border=True):
            c_info, c_btns = st.columns([3, 1])
            with c_info:
                st.markdown(f"**🐺 {kw}**")
                st.caption(f"🔗 {url[:55]}...")
                card_placeholders[rid] = st.empty()
                
            with c_btns:
                b_cols = st.columns(3)
                if b_cols[0].button("🐺", key=f"olf_f_{rid}", width="stretch"):
                    res_ind = hunt_offers(url, kw, p_max, es_pro=("business" in familia_raw.lower()), headless=FORCE_HEADLESS)
                    st.session_state[f"last_res_{rid}"] = res_ind
                    st.rerun()
                if b_cols[1].button("✏️", key=f"edit_f_{rid}", width="stretch"):
                    st.session_state["editing_caza"] = b
                    st.rerun()
                if b_cols[2].button("🗑️", key=f"del_f_{rid}", width="stretch"):
                    supabase.table("cazas").delete().eq("id", b["id"]).execute()
                    st.rerun()

            res = st.session_state.get(f"last_res_{rid}", [])
            if res:
                with st.expander(f"✅ Resultados ({len(res)})"):
                    for r in res[:5]:
                        r1, r2 = st.columns([4, 1])
                        r1.write(f"**{r.get('title')[:65]}** - ${int(r.get('price', 0)):,}")
                        r2.link_button("Ver", get_affiliate_url(r.get("url")), width="stretch")

# ==========================================================
# FINAL / SONIDO
# ==========================================================
if st.session_state.get("play_sound"):
    play_wolf_sound(); st.session_state["play_sound"] = False

if not st.session_state.get("busquedas"):
    st.info("No tenés cacerías activas. Creá una arriba para empezar. 🐺")

render_footer()