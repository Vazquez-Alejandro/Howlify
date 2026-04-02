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

from auth.supabase_client import supabase # Importante que esté después de load_dotenv()
from auth.auth_supabase import supa_signup, supa_login, supa_reset_password
from db.database import obtener_cazas, save_user_telegram, get_user_profile
from scraper.scraper_pro import hunt_offers
from config import PLAN_LIMITS
from services.business_service import obtener_top_oportunidades
from services.whatsapp_service import enviar_whatsapp
from services.telegram_service import enviar_telegram
from utils.affiliate import get_affiliate_url
from services.duffel_service import buscar_ofertas_vuelos

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
    
    # Creamos un mapa unificado por ID (clave para que todo funcione)
    rules_map = {str(r.get("caza_id")): r for r in rules_data if r.get("caza_id")}
    rules_by_url = {str(r.get("product_url")): r for r in rules_data if r.get("product_url")}

    radar_rows = []
    for b in busquedas:
        bid = str(b.get("id") or "")
        p_url = b.get("link") or b.get("url") or ""
        
        # Buscamos la regla por ID o por URL como respaldo
        rule = rules_map.get(bid) or rules_by_url.get(p_url) or {}
        
        # Obtener precio actual
        res_p = supabase.table("price_history").select("price").eq("caza_id", bid).order("checked_at", desc=True).limit(1).execute()
        curr_p = float(res_p.data[0]["price"]) if res_p.data else 0.0
        
        m_p = float(rule.get("min_price_allowed") or 0.0)
        max_p = float(rule.get("max_price_allowed") or 0.0)

        # SEMÁFORO
        if curr_p <= 0: riesgo = "⚪"
        elif m_p > 0 and curr_p < m_p: riesgo = "🔴"
        elif max_p > 0 and curr_p > max_p: riesgo = "🟠"
        else: riesgo = "🟢"

        # PROGRESO
        progreso = 0.0
        if m_p > 0 and max_p > m_p:
            progreso = max(0.0, min(1.0, (curr_p - m_p) / (max_p - m_p)))

        radar_rows.append({
            "Riesgo": riesgo,
            "ID": bid,
            "Producto": (b.get("producto") or b.get("keyword") or "SIN NOMBRE").upper(),
            "URL": p_url,
            "Precio": curr_p,
            "Mín. MAP": m_p,
            "Máximo": max_p,
            "Rango": progreso,
            "raw_data": b,
            "full_id": bid
        })

    # ==========================================================
    # 2. RENDER DE TABLA
    # ==========================================================
    df_radar = pd.DataFrame(radar_rows)
    
    if not df_radar.empty:
        orden_prioridad = {"🔴": 0, "🟠": 1, "🟡": 2, "🟢": 3, "⚪": 4}
        df_radar["orden"] = df_radar["Riesgo"].map(orden_prioridad)
        df_radar = df_radar.sort_values("orden")

        df_display = df_radar.drop(columns=["raw_data", "full_id", "orden"], errors='ignore')

        # TABLA FINAL BLINDADA (Compatibilidad asegurada)
        st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            key="radar_table_clean",
            disabled=["Riesgo", "ID", "Producto", "URL", "Precio", "Rango"], 
            column_config={
                "URL": st.column_config.LinkColumn("Enlace"),
                "Precio": st.column_config.NumberColumn(format="$%d"),
                "Mín. MAP": st.column_config.NumberColumn(format="$%d"),
                "Máximo": st.column_config.NumberColumn(format="$%d"),
                "Rango": st.column_config.ProgressColumn("Posición", min_value=0, max_value=1),
            },
            column_order=("Riesgo", "ID", "Producto", "URL", "Precio", "Mín. MAP", "Máximo", "Rango")
        )

        # ==========================================================
        # 3. SELECCIÓN & ANÁLISIS DINÁMICO
        # ==========================================================
        state = st.session_state.get("radar_table_clean", {})
        sel_rows = state.get("selection", {}).get("rows", [])
        idx = sel_rows[0] if sel_rows else 0

        if idx >= len(df_radar): 
            idx = 0

        selected_row = df_radar.iloc[idx]
        cid = selected_row["full_id"]
        current_keyword = selected_row["Producto"]
        curr_price = float(selected_row["Precio"])
            
        # Usamos el mapa unificado definido arriba en la función
        rule = rules_map.get(str(cid)) or {}
        min_p = float(rule.get("min_price_allowed") or 0)
        max_p = float(rule.get("max_price_allowed") or 0)
        c_row = selected_row["raw_data"]

        st.divider()
        st.markdown(f"### 🔍 Detalle: {current_keyword}")

        # Métrica de Compliance e Historial
        res_hist = supabase.table("price_history").select("checked_at, price").eq("caza_id", cid).order("checked_at").execute()
        df_hist = pd.DataFrame(res_hist.data or [])

        compliance_rate = 100
        if not df_hist.empty and min_p > 0:
            compliance_rate = int((len(df_hist[df_hist["price"] >= min_p]) / len(df_hist)) * 100)

        # Colores de métricas
        if curr_price <= 0: color, txt = "#808080", "SIN DATOS"
        elif min_p > 0 and curr_price < min_p: color, txt = "#FF4B4B", "MAP VIOLADO"
        elif max_p > 0 and curr_price > max_p: color, txt = "#FFA500", "SOBREPRECIO"
        else: color, txt = "#28A745", "CUMPLIMIENTO OK"

        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(f"<small>Actual</small><h3>${int(curr_price)}</h3>", unsafe_allow_html=True)
        with k2: st.markdown(f"<small>Estado</small><h3 style='color:{color}; font-size:18px;'>{txt}</h3>", unsafe_allow_html=True)
        with k3: st.markdown(f"<small>Mínimo MAP</small><h3>${int(min_p)}</h3>", unsafe_allow_html=True)
        with k4: st.markdown(f"<small>Compliance</small><h3>{compliance_rate}%</h3>", unsafe_allow_html=True)

        with st.form("config_rules"):
            st.caption(f"⚙️ Configuración para: {current_keyword}")
            c1, c2 = st.columns(2)
            f_min = c1.number_input("MAP (Mínimo)", value=int(min_p), step=1000)
            f_max = c2.number_input("Techo (Máximo)", value=int(max_p), step=1000)

            if st.form_submit_button("💾 Guardar Reglas", use_container_width=True):
                if not cid:
                    st.error("No se detectó un ID válido.")
                else:
                    # 1. Limpieza manual garantizada
                    supabase.table("monitor_rules").delete().filter("caza_id", "eq", int(cid)).execute()
                
                    # 2. Creación de objeto limpio
                    nueva_regla = {
                        "caza_id": int(cid),
                        "user_id": user_id,
                        "min_price_allowed": float(f_min),
                        "max_price_allowed": float(f_max),
                        "product_name": str(current_keyword),
                        "product_url": str(c_row.get("link") or "")
                    }
                
                    # 3. Inserción directa
                    res = supabase.table("monitor_rules").insert(nueva_regla).execute()
                    
                    if res.data:
                        st.success(f"✅ ¡Configuración para {current_keyword} actualizada!")
                        st.rerun()
                    else:
                        st.error("Error: No se pudo insertar en la base de datos.")

        if not df_hist.empty:
            df_hist["checked_at"] = pd.to_datetime(df_hist["checked_at"])
            import altair as alt
            chart = alt.Chart(df_hist).mark_line(point=True, color="#ff4b4b").encode(
                x=alt.X('checked_at:T', title="Tiempo"),
                y=alt.Y('price:Q', scale=alt.Scale(zero=False), title="Precio ($)")
            )
            if min_p > 0:
                rule_line = alt.Chart(pd.DataFrame({'y': [min_p]})).mark_rule(color='red', strokeDash=[5,5]).encode(y='y:Q')
                chart += rule_line
            st.altair_chart(chart.interactive(), use_container_width=True)
    else:
        st.info("Esperando datos de los rastreadores...")
            
def render_business_dashboard(plan: str, plan_label_text: str, user_id: str, busquedas: list):
    if plan == "business_monitor":
        render_business_monitor_dashboard(plan_label_text, user_id, busquedas)
    else:
        st.subheader("📊 Business Dashboard · Reseller")
        if st.button("Buscar Oportunidades 🚀", use_container_width=True):
            with st.spinner("Olfateando mercado..."):
                ops = obtener_top_oportunidades(user_id)
                if ops:
                    for o in ops: st.success(f"🔥 {o['title']} - {o['price_fmt']}")
                else: st.info("No hay brechas críticas hoy.")

# ==========================================================
# SUPABASE HELPERS
# ==========================================================

# ==========================================================
# 📊 DATA HELPERS PARA EL DASHBOARD
# ==========================================================
def get_price_history_series_by_caza(user_id, caza_id):
    """Trae el historial para graficar"""
    try:
        # La barra invertida tiene que estar al final de cada línea de código real
        res = supabase.table("price_history") \
            .select("checked_at, price") \
            .eq("caza_id", caza_id) \
            .order("checked_at", desc=False) \
            .execute()
        
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            df["checked_at"] = pd.to_datetime(df["checked_at"])
            df["price"] = pd.to_numeric(df["price"], errors='coerce')
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

def guardar_caza_supabase(
    user_id: str,
    producto: str,
    url: str,
    precio_max,
    frecuencia: str,
    tipo_alerta: str,
    plan: str,
    source: str | None = None,
):
    try:
        if not user_id:
            return False

        rules = get_effective_plan_rules(plan)
        max_cazas = int(rules["max_cazas_activas"])
        source = (source or DEFAULT_SOURCE).strip().lower()

        activas = contar_cazas_activas(user_id)
        if activas >= max_cazas:
            return "limite"

        precio_int = parse_price_to_int(precio_max)

        payload = {
            "user_id": user_id,
            "producto": (producto or "").strip(),
            "link": (url or "").strip(),
            "precio_max": precio_int,
            "frecuencia": (frecuencia or "").strip(),
            "tipo_alerta": (tipo_alerta or "piso").strip().lower(),
            "plan": rules["plan_key"],
            "estado": "activa",
            "source": source,
            "last_check": None,
        }

        ins = supabase.table("cazas").insert(payload).execute()

        if getattr(ins, "data", None):
            print("[guardar_caza_supabase] insert ok:", ins.data)
            return True

        print("[guardar_caza_supabase] insert sin data:", ins)
        return False

    except Exception as e:
        print("[guardar_caza_supabase] error:", e)
        return False
    
def run_manual_hunt(b, headless=True):
    url = b.get("url") or b.get("link") or ""
    kw = b.get("keyword") or b.get("producto") or ""
    precio = b.get("precio_max") or 0
    
    plan_str = b.get('plan', 'starter').lower()
    es_pro_real = (plan_str in ["pro", "business"])

    # Pasamos el headless a hunt_offers
    return hunt_offers(url, kw, precio, es_pro=es_pro_real, headless=headless)
  

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

    .oh-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 20px;
        padding: 22px 22px 18px 22px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.22);
        min-height: 265px;
        transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }

    .oh-card:hover {
        transform: translateY(-4px);
        border-color: rgba(255,255,255,0.24);
        box-shadow: 0 18px 40px rgba(0,0,0,0.35);
    }

    .oh-card h3 {
        margin-top: 0;
        margin-bottom: 0.6rem;
        font-size: 1.2rem;
    }

    .oh-card p {
        opacity: 0.94;
        line-height: 1.5;
        margin-bottom: 0.5rem;
    }

    .oh-badge {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 5px 10px;
        border-radius: 999px;
        background: rgba(255,255,255,0.12);
        margin-bottom: 10px;
    }

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
                <p>Encontrá ofertas, configurá cacerías y recibí alertas automáticas.</p>
                <p>Ideal para usuarios que quieren comprar mejor y detectar oportunidades sin complicarse.</p>
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
                <p>Monitoreá precios, detectá oportunidades y analizá mercados.</p>
                <p>Ideal para revendedores, marcas y empresas que necesitan inteligencia de precios.</p>
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
                <p>✅ 5 cazas activas<br>
                ✅ Frecuencia mínima 1 hora<br>
                ✅ MercadoLibre + generic<br>
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
                <p>✅ 15 cazas activas<br>
                ✅ Frecuencia mínima 15 min<br>
                ✅ MercadoLibre + generic<br>
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
                <p>✅ Detección de oportunidades<br>
                ✅ Historial de precios<br>
                ✅ Alertas avanzadas<br>
                ✅ Enfoque en reventa</p>
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
                <p>✅ Monitoreo de precios<br>
                ✅ Ranking de oportunidades<br>
                ✅ Seguimiento de mercado<br>
                ✅ Enfoque en marcas y empresas</p>
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
# 📲 PANEL DE ALERTAS UNIFICADO (TELEGRAM + WA/EMAIL)
# ==========================================================

_wa_val = st.session_state.get("whatsapp_number", (profile.get("whatsapp_number") or "").strip())
_tg_val = st.session_state.get("telegram_id", (profile.get("telegram_id") or "").strip())

with st.expander("📲 Configuración de Alertas", expanded=not bool(_wa_val or _tg_val)):
    st.caption("Configurá tus canales de recepción para que el Lobo te avise al instante.")
    
    col_tg, col_wa_em = st.columns(2)

    # --- COLUMNA 1: TELEGRAM ---
    with col_tg:
        st.markdown("#### 📱 Telegram")
        nuevo_id_tg = st.text_input(
            "ID de Telegram",
            value=_tg_val,
            help="Hablale a @GetMyIDBot para conseguir tu ID",
            key="tg_unificado_input_v2"
        )
        
        c_tg1, c_tg2 = st.columns(2)
        with c_tg1:
            # CAMBIO AQUÍ: use_container_width=True
            if st.button("💾 Guardar ID", key="btn_save_tg_v2", use_container_width=True):
                if save_user_telegram(user_id, nuevo_id_tg):
                    st.session_state["telegram_id"] = nuevo_id_tg
                    st.success("✅ Guardado")
                    st.rerun()
        with c_tg2:
            if _tg_val:
                # CAMBIO AQUÍ: use_container_width=True
                if st.button("🧪 Probar ID", key="btn_test_tg_v2", use_container_width=True):
                    from services.telegram_service import enviar_telegram
                    p_tg = {"title": "Prueba Ninja 🐺", "price": 0, "url": "https://howlify.app"}
                    if enviar_telegram(_tg_val, p_tg, "Test"):
                        st.toast("¡Aullido enviado!", icon="✅")

    # --- COLUMNA 2: WHATSAPP O EMAIL ---
    with col_wa_em:
        if rules["features"].get("whatsapp_alerts", False):
            st.markdown("#### 🟢 WhatsApp")
            wa_input = st.text_input(
                "Número de WhatsApp",
                value=_wa_val,
                placeholder="54911XXXXXXXX",
                key="wa_number_v2",
            )

            # CAMBIO AQUÍ: use_container_width=True
            if st.button("💾 Guardar WhatsApp", key="btn_save_wa_v2", use_container_width=True):
                from db.database import normalize_phone 
                numero = normalize_phone(wa_input)
                if not numero:
                    st.error("Ingresá un número válido.")
                else:
                    if save_user_whatsapp(user_id, numero):
                        st.session_state["whatsapp_number"] = numero
                        st.success("✅ Guardado")
                        st.rerun()

            if _wa_val:
                # CAMBIO AQUÍ: use_container_width=True
                if st.button("🧪 Probar WA", key="btn_test_wa_v2", use_container_width=True):
                    from services.whatsapp_service import enviar_whatsapp
                    p_wa = {"title": "Prueba Ninja 🐺", "price": 0, "url": "https://howlify.app"}
                    if enviar_whatsapp(numero=_wa_val, oferta=p_wa, caza_nombre="Test"):
                        st.toast("¡WhatsApp enviado!", icon="✅")
        else:
            st.markdown("#### 📧 Email")
            st.info(f"Alertas activas para: \n**{email}**")
            st.caption("Actualizá a Pro para desbloquear WhatsApp.")


# ==========================================================
# VISTA: EL MONITOR (Tus cacerías)
# ==========================================================
# Si el código llega hasta acá, es porque estamos en "Mis Rastreadores",
# así que dejamos que dibuje todo lo de abajo normalmente.

st.write("") # Un espaciador sutil para que no quede pegado arriba

# ==========================================================
# NUEVA CAZA
# ==========================================================

total_ocupado = cazas_activas

if total_ocupado < limite_plan:
    with st.expander("➕ Configurar nueva cacería"):
        n_url = st.text_input("URL")
        n_key = st.text_input("Palabra clave")

        tipo_alerta_ui = st.radio("Estrategia:", ["Precio Piso", "Descuento %"], horizontal=True)

        if tipo_alerta_ui == "Precio Piso":
            n_price = st.number_input(
                "Precio Máximo ($)",
                min_value=0,
                value=500000,
                step=1000,
                key="price_piso",
            )
            # --- EL TOQUE DE UX ---
            st.caption(f"🎯 Alertar si el precio baja de: **{_fmt_money(n_price)}**")
            # ----------------------
            tipo_db = "piso"
            
        else:
            n_price = st.slider("Porcentaje deseado (%)", 5, 90, 35, key="price_desc")
            tipo_db = "descuento"

        n_freq = st.selectbox("Frecuencia", rules["freq_options"])

        if DEBUG:
            st.caption(f"DEBUG UI | tipo_db={tipo_db} | n_price={n_price} | type={type(n_price)}")

        if st.button("Lanzar", use_container_width=True):
            if not n_url.strip():
                st.error("Ingresá una URL.")
                st.stop()

            if not n_key.strip():
                st.error("Ingresá una palabra clave.")
                st.stop()

            precio_max = parse_price_to_int(n_price)

            if tipo_db == "piso" and precio_max <= 0:
                st.error("El precio máximo debe ser mayor a 0.")
                st.stop()

            src = infer_source_from_url(n_url)
            if src == "unknown":
                src = DEFAULT_SOURCE

            # 1. Guardamos en la base de datos
            resultado = guardar_caza_supabase(
                user_id=user_id,
                producto=n_key,
                url=n_url,
                precio_max=precio_max,
                frecuencia=n_freq,
                tipo_alerta=tipo_db,
                plan=plan,
                source=src,
            )

            if resultado is True:
                # 2. Avisamos que se guardó bien
                st.success("✅ Caza guardada correctamente.")
                
                # 3. Actualizamos la lista local para que aparezca abajo
                st.session_state["busquedas"] = obtener_cazas(user_id, plan_real_raw) or []
                
                # 4. Limpiamos la pantalla (opcional) para que el formulario quede listo para otra carga
                st.rerun() 
                
            elif resultado == "limite":
                st.warning("⚠️ Alcanzaste el límite de tu plan.")
            else:
                st.error("❌ Error al guardar la caza.")
else:
    st.warning(f"Has alcanzado el límite de {limite_plan} búsquedas de tu plan {rules['label']}.")

# ==========================================================
# LISTADO / OLFATEAR (VERSIÓN DINÁMICA PRO - SIN GRISADO)
# ==========================================================

# 1. Contenedor superior para el botón y barra de progreso
top_zone = st.container()
status_slot = st.empty()

# Diccionario para mapear cada card con su espacio de actualización
card_placeholders = {}

# 2. RENDERIZADO DE LAS CARDS (Las dibujamos primero para generar los slots)
if st.session_state.get("busquedas"):
    st.subheader(f"Mis Cacerías ({rules['label']})")

    for i, b in enumerate(st.session_state["busquedas"]):
        rid = str(b.get("id", i))

        with st.container(border=True):
            col_info, col_btns = st.columns([3, 1])

            with col_info:
                p_raw = b.get("precio_max", 0)
                tipo = (b.get("tipo_alerta") or "piso").strip().lower()
                
                try:
                    p_val = int(float(p_raw))
                    label_precio = f"Máx: ${p_val:,}".replace(",", ".") if tipo == "piso" else f"Objetivo: {p_val}% desc."
                except:
                    label_precio = f"Objetivo: {p_raw}"

                kw = b.get("keyword") or b.get("producto") or "Sin nombre"
                url = b.get("url") or b.get("link") or ""
                
                st.markdown(f"**🐺 {kw.upper()}** ({tipo.capitalize()})")
                st.caption(f"🔗 {url[:60]}...")
                st.write(f"🎯 {label_precio} | ⏱️ {b.get('frecuencia', 'Manual')}")
                
                # --- EL SLOT MÁGICO ---
                # Este espacio se actualizará en tiempo real durante la búsqueda masiva
                card_placeholders[rid] = st.empty()
                
                # Si ya hay resultados previos, mostramos un resumen leve
                old_res = st.session_state.get(f"last_res_{rid}", [])
                if old_res:
                    with card_placeholders[rid]:
                        st.caption(f"✨ {len(old_res)} ofertas en cache.")

            with col_btns:
                c_olf, c_edit, c_del = st.columns(3)

                with c_olf:
                    # OLFATEAR INDIVIDUAL
                    if st.button("🐺", key=f"olf_{rid}", use_container_width=True):
                        st.session_state["editing_caza"] = None
                        status_slot.info(f"⏳ El Lobo está rastreando {kw}...")
                        try:
                            with st.spinner(""):
                                kw2, url2 = kw, url
                                precio2 = parse_price_to_int(p_raw)
                                plan_real = b.get('plan', 'starter').lower()
                                es_pro_real = (plan_real in ["pro", "business"])

                                resultados = hunt_offers(url2, kw2, precio2, es_pro=es_pro_real, headless=FORCE_HEADLESS) or []
                                st.session_state[f"last_res_{rid}"] = resultados
                                st.session_state["last_updated_rid"] = rid
                                if resultados and st.session_state.get("sound_enabled", True):
                                    st.session_state["sound_tick"] += 1
                                    st.session_state["play_sound"] = True
                                st.rerun()
                        except Exception as e:
                            status_slot.error(f"❌ Error: {str(e)}")

                with c_edit:
                    if st.button("✏️", key=f"edit_{rid}", use_container_width=True):
                        st.session_state["editing_caza"] = b
                        st.rerun()

                with c_del:
                    if st.button("🗑️", key=f"del_{rid}", use_container_width=True):
                        supabase.table("cazas").delete().eq("id", b["id"]).execute()
                        st.session_state["busquedas"] = [x for x in st.session_state["busquedas"] if str(x.get("id")) != rid]
                        st.rerun()

            # RESULTADOS (Debajo de cada card)
            res = st.session_state.get(f"last_res_{rid}", []) or []
            if res:
                with st.expander(f"✅ Resultados ({len(res)})", expanded=False):
                    for r in res[:10]:
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.markdown(f"**{str(r.get('title'))[:80]}**")
                            st.caption(f"Precio: ${int(r.get('price', 0)):,}".replace(",", "."))
                        with c2:
                            st.link_button("Ver", get_affiliate_url(r.get("url")), use_container_width=True)

# 3. LÓGICA DEL BOTÓN MASIVO (En la zona superior)
with top_zone:
    if st.button("🔎 Olfatear todas mis cazas", use_container_width=True):
        busquedas = st.session_state.get("busquedas", []) or []
        if not busquedas:
            st.info("No tenés cazas.")
        else:
            encontro_total = False
            progreso_bar = st.progress(0)
            
            for i, b in enumerate(busquedas):
                rid = str(b.get("id", i))
                kw = b.get("keyword") or b.get("producto") or "Producto"
                
                # Feedback visual en la card específica
                with card_placeholders[rid]:
                    st.warning(f"⏳ Olfateando...")
                
                progreso_bar.progress((i + 1) / len(busquedas))

                try:
                    # LLAMADA AL MOTOR
                    resultados = run_manual_hunt(b, headless=FORCE_HEADLESS) or []
                    st.session_state[f"last_res_{rid}"] = resultados
                    
                    # ACTUALIZACIÓN EN VIVO DE LA CARD
                    with card_placeholders[rid]:
                        if resultados:
                            encontro_total = True
                            st.success(f"✅ ¡{len(resultados)} nuevas!")
                        else:
                            st.info("🌑 Sin ofertas.")

                    save_price_history(user_id=user_id, caza_id=b.get("id"), results=resultados)
                except:
                    with card_placeholders[rid]: st.error("❌ Error")
                    continue

            # AULLIDO FINAL
            if encontro_total and st.session_state.get("sound_enabled", True):
                st.session_state["sound_tick"] += 1
                st.session_state["play_sound"] = True
            
            progreso_bar.empty()
            st.rerun()

# ==========================================================
# SONIDO / EMPTY STATE
# ==========================================================

if st.session_state.get("play_sound"):
    play_wolf_sound()
    st.session_state["play_sound"] = False
else:
    if not st.session_state["busquedas"]:
        st.info("Todavía no tenés cacerías activas. Creá una arriba para empezar a olfatear ofertas. 🐺")


# Renderizar el footer al final de la página
render_footer() 