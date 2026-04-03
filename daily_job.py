# daily_job.py
from services.database_service import ejecutar_reporte_diario_total
import os

if __name__ == "__main__":
    print("🌕 El Lobo está despertando para el reporte diario...")
    ejecutar_reporte_diario_total()
    print("🌑 Reporte finalizado.")