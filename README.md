🐺 Howlify v1.2.0-beta
Howlify is a high-performance price monitoring and flight search engine. Designed for deal hunters, it combines web scraping with professional travel APIs to find the best opportunities in real-time.

🛠️ Tech Stack
Language: Python 3.10+

Framework: Streamlit (Web Interface)

APIs: Duffel API (Direct Airline Connection) & DolarApi (Real-time ARS Conversion)

Database: Supabase / SQLite3 (Persistence & Hunt history)

Scraping: Playwright / BeautifulSoup4

🚀 Key Features
✈️ Travel & Flights
Smart Flight Router: Integrated search for Despegar, Almundo, Turismocity, Avantrip, and Smiles.

Professional Flight Data: Real-time airline offers via Duffel API (Direct NDC).

Auto-Currency Conversion: Prices automatically converted to Argentine Pesos (ARS) using the "Dólar Tarjeta" rate.

🛒 E-Commerce Intelligence (New!)
Hybrid ML Scraper: Smart routing that distinguishes between Direct Product Links (Deep Scan) and Search Result Listings (Massive Hunt).

Multi-Context Spoofing (Pro Feature): Parallel scraping using multiple "disguises" (Desktop & iPhone 13) to bypass anti-bot measures and find hidden mobile-only deals.

Tiered Search Logic: Dynamic plan detection (Starter/Pro/Business) that unlocks advanced scraping layers and frequency.

Anti-Fraud Shield: Real-time seller reliability analysis during direct product scans.

🛡️ Core Infrastructure
Affiliate Ready: Built-in deep linking architecture for monetization.

Multi-Target Tracking: Monitor products and flights across different platforms simultaneously.

Security: SHA-256 Hashing, Age verification, and Regex-based validation.

📥 Installation
Clone the repository:

Bash
git clone https://github.com/vazquez-alejandro/howlify.git
cd howlify
Set up virtual environment:

Bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
Install dependencies:

Bash
pip install -r requirements.txt
playwright install chromium
Environment Variables:
Create a .env file with your Supabase and Duffel credentials.

Run the App:

Bash
streamlit run app.py
