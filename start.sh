#!/bin/bash
# Arrancamos el bot de Telegram de fondo
python scripts/telegram_connect.py &

# Arrancamos Streamlit normalmente
streamlit run app.py --server.port $PORT --server.address 0.0.0.0