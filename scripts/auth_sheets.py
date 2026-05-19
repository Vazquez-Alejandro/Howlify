"""
Autenticación inicial para Google Sheets.
Corré esto UNA SOLA VEZ para generar token.json.
"""
import os
import json
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credenciales.json")

if not os.path.exists(creds_path):
    print(f"❌ No se encuentra {creds_path}")
    print("Descargalo desde Google Cloud > Credenciales > ID de cliente OAuth > Aplicación de escritorio")
    exit(1)

from google_auth_oauthlib.flow import InstalledAppFlow

import webbrowser

flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
try:
    creds = flow.run_local_server(port=0, open_browser=True)
except webbrowser.Error:
    print("🔗 Abrí este link en tu navegador para autorizar:")
    print(flow.authorization_url()[0])
    creds = flow.run_local_server(port=0, open_browser=False)

token_path = "token.json"
with open(token_path, "w") as f:
    f.write(creds.to_json())

print(f"✅ Token guardado en {token_path}")
print("Ya podés usar el botón '📤 Exportar' en el dashboard.")
