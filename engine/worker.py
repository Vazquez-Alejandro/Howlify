import time
import signal
import sys

from engine import start_engine


def main():
    print("🐺 PriceLobo Monitor starting...")
    
    # Definimos cada cuánto tiempo queremos que verifique precios (ej: cada 30 min)
    INTERVALO_SEGUNDOS = 1800 

    while True:
        print(f"🔍 [{time.strftime('%H:%M:%S')}] Iniciando ronda de vigilancia...")
        
        try:
            # Llamamos al engine para que procese las "cazas" actuales
            # Importante: Asegurate que start_engine() ejecute el scraper y guarde en price_history
            start_engine(run_once=True)
            
            print(f"✅ Ronda completada. Próxima revisión en {INTERVALO_SEGUNDOS/60} min.")
        except Exception as e:
            print(f"❌ Error durante el monitoreo: {e}")

        # El proceso se queda esperando hasta la próxima ronda
        time.sleep(INTERVALO_SEGUNDOS)

def _handle_exit(signum, frame):
    print(f"🛑 Worker received signal {signum}. Shutting down...")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)

    main()