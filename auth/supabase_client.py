import os
from pathlib import Path
from dotenv import load_dotenv
import httpx
from supabase import create_client

# ==========================================================
# CONFIGURACIÓN DE ENV
# ==========================================================

# Configuración de Paths para el .env
CURRENT_FILE = Path(__file__).resolve()
ROOT_ENV = CURRENT_FILE.parents[2] / ".env"
PACKAGE_ENV = CURRENT_FILE.parents[1] / ".env"

if ROOT_ENV.exists():
    load_dotenv(dotenv_path=ROOT_ENV)
elif PACKAGE_ENV.exists():
    load_dotenv(dotenv_path=PACKAGE_ENV)
else:
    load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en el .env")

# ==========================================================
# CLIENTES SUPABASE
# ==========================================================

# Cliente para usuarios (login, cazas, perfiles) → requiere refresh
supabase_user = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
# Cliente para panel admin (usuarios, métricas, reportes globales) → no expira
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Forzar HTTP/1.1 para evitar desconexiones HTTP/2 con Supabase
for client in [supabase_user, supabase_admin]:
    client.postgrest.session = httpx.Client(http2=False)

# Alias por compatibilidad (usa service role por defecto)
supabase = supabase_admin
