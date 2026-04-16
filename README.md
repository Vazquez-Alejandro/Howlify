🐺 Howlify v1.3.0-beta

Howlify is a high-performance price monitoring and notification engine. Designed for deal hunters, it combines advanced web scraping with real-time multi-channel alerts to catch the best opportunities before they vanish.
🛠️ Tech Stack & Infrastructure

    Language: Python 3.10+

    Framework: Streamlit (Pro Web Interface)

    Database: Supabase (PostgreSQL) with RLS & Service Role architecture.

    Automation: Cron-job.org (External trigger for high-frequency monitoring).

    Hosting: Render (Cloud Deployment).

🚀 Key Features
✈️ Travel & Flights

    Smart Flight Router: Integrated search for Despegar, Almundo, Turismocity, and Smiles.

    Professional Flight Data: Real-time airline offers via Duffel API (Direct NDC).

    Auto-Currency Conversion: Prices automatically converted to ARS using DolarApi (Dólar Tarjeta rate).

🛒 E-Commerce Intelligence (ML Specialist)

    Hybrid ML Scraper: Smart routing for Mercado Libre (Deep Scan vs. Search Results).

    Multi-Context Spoofing: Parallel scraping (Desktop/iPhone) to bypass anti-bot measures.

    Anti-Fraud Shield: Real-time seller reliability and reputation analysis.

🔔 Smart Notification System (New!)

    Telegram Bot Integration: One-click account linking (/start auto-sync) and instant deal alerts via Telegram Bot API.

    Multi-Channel Alerts: Support for WhatsApp Cloud API (Meta) and Resend/SMTP for critical price drops.

    User Persistence: Dedicated profile management in Supabase to track individual "Hunts".

📥 Installation

    Clone & Setup:

Bash

git clone https://github.com/vazquez-alejandro/howlify.git
cd howlify
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

    Environment Variables:
    Create a .env file with the following keys:

Fragmento de código

SUPABASE_URL=your_url
SUPABASE_SERVICE_ROLE_KEY=your_key
TELEGRAM_TOKEN=your_bot_token
DUFFEL_TOKEN=your_token

    Run the App:

Bash

streamlit run app.py

    Background Connect (Telegram):
    To keep the bot listening for new users:

Bash

python3 scripts/telegram_connect.py