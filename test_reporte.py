# test_reporte.py modificado para saltear el error de engine
import os
from services.database_service import ejecutar_reporte_diario_total

# Forzamos un mock de la función que falla o simplemente comentá el envío de telegram 
# en database_service.py un segundo.

print("🐺 Intentando disparo forzado...")
try:
    ejecutar_reporte_diario_total(force=True)
except Exception as e:
    print(f"Fallo el test: {e}")