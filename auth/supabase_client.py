import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

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

# USAMOS LA SERVICE ROLE KEY POR DEFECTO
# Esto permite que el Bot actualice perfiles aunque el RLS esté activo
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Mantenemos este por compatibilidad si lo usás en otro lado
supabase_admin = supabase