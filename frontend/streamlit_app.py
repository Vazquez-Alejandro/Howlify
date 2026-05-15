import os
import re
import time
import requests
from datetime import datetime
from urllib.parse import urlparse
import streamlit as st

API_URL = os.getenv("HOWLIFY_API_URL", "http://localhost:8000")
st.set_page_config(page_title="Howlify · API Client", layout="centered", page_icon="🐺")

if "token" not in st.session_state:
    st.session_state["token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None

def api_headers():
    return {"Authorization": f"Bearer {st.session_state['token']}"} if st.session_state["token"] else {}

def api_get(path):
    try:
        r = requests.get(f"{API_URL}{path}", headers=api_headers(), timeout=30)
        return r.json() if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}

def api_post(path, data=None):
    try:
        r = requests.post(f"{API_URL}{path}", json=data, headers=api_headers(), timeout=120)
        return r.json() if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}

def api_delete(path):
    try:
        r = requests.delete(f"{API_URL}{path}", headers=api_headers(), timeout=30)
        return r.json() if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}

st.title("🐺 Howlify · API Client")
st.caption("Thin client conectado a la API")

if not st.session_state["token"]:
    tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
    with tab1:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                res = api_post("/api/auth/login", {"email": email, "password": password})
                if "token" in res:
                    st.session_state["token"] = res["token"]
                    st.session_state["user"] = res["user"]
                    st.rerun()
                else:
                    st.error(res.get("detail", "Error al iniciar sesión"))
    with tab2:
        with st.form("signup"):
            u = st.text_input("Usuario")
            e = st.text_input("Email")
            p = st.text_input("Contraseña", type="password")
            plan = st.selectbox("Plan", ["starter", "pro"])
            if st.form_submit_button("Crear Cuenta", type="primary"):
                res = api_post("/api/auth/signup", {"email": e, "password": p, "username": u, "plan": plan})
                if "message" in res:
                    st.success(res["message"])
                else:
                    st.error(res.get("detail", "Error al registrar"))
    st.stop()

st.success(f"Conectado como {st.session_state['user'].get('email', '')}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state["token"] = None
    st.session_state["user"] = None
    st.rerun()

# ─── Cazas ──────────────────────────────────────────────

st.subheader("🎯 Mis Cacerías")
cazas = api_get("/api/cazas").get("cazas", [])

if cazas:
    for c in cazas:
        kw = (c.get("producto") or c.get("keyword") or "Sin nombre").upper()
        url = c.get("link") or c.get("url") or ""
        with st.container(border=True):
            cols = st.columns([3, 1])
            cols[0].markdown(f"**🐺 {kw}**")
            cols[0].caption(f"🔗 {url[:55]}...")
            if cols[1].button("🐺 Olfatear", key=f"hunt_{c.get('id')}"):
                with st.spinner("Olfateando..."):
                    res = api_post(f"/api/hunt/{c.get('id')}")
                    results = res.get("results", [])
                    if results:
                        for r in results[:5]:
                            st.write(f"• ${int(r.get('price', 0)):,} — {r.get('title', '')[:60]}")
                        st.success(f"✅ {len(results)} resultados")
                    else:
                        st.info("Sin resultados")
else:
    st.info("No tenés cacerías activas")

# ─── Nueva cacería ──────────────────────────────────────

with st.expander("➕ Nueva Cacería"):
    with st.form("new_caza"):
        kw = st.text_input("Nombre / Etiqueta")
        url = st.text_input("URL")
        pmax = st.number_input("Precio Máximo", min_value=0, value=50000, step=1000)
        freq = st.selectbox("Frecuencia", ["1 h", "2 h", "4 h", "12 h"])
        if st.form_submit_button("Crear"):
            res = api_post("/api/cazas", {"keyword": kw, "url": url, "precio_max": pmax, "frecuencia": freq})
            if "message" in res:
                st.success(res["message"])
                time.sleep(1)
                st.rerun()
            else:
                st.error(res.get("detail", str(res)))

# ─── Health check ────────────────────────────────────────

st.divider()
health = api_get("/api/health")
if "status" in health:
    st.caption(f"API: {health['status']} · {health.get('timestamp', '')}")
