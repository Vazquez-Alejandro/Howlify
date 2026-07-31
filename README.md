# Howlify

**Price Intelligence & Deal Alert Engine** for Latin America.

Howlify monitors prices across MercadoLibre, flights via Duffel API, and Airbnb listings, sending real-time alerts when prices drop below user-defined thresholds.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HOWLIFY STACK                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frontend (React + Vite)          Backend (FastAPI)         │
│  ┌──────────────────┐             ┌──────────────────┐     │
│  │  React 19        │             │  FastAPI          │     │
│  │  Tailwind CSS    │◄───API────►│  Python 3.12      │     │
│  │  React Query     │             │  Celery Workers   │     │
│  │  Framer Motion   │             │  Playwright       │     │
│  │  Vite            │             │                   │     │
│  └──────────────────┘             └──────────────────┘     │
│           │                               │                 │
│           ▼                               ▼                 │
│  ┌──────────────────┐             ┌──────────────────┐     │
│  │  Vercel          │             │  Supabase        │     │
│  │  (Hosting)       │             │  (PostgreSQL)    │     │
│  └──────────────────┘             └──────────────────┘     │
│                                                             │
│  External APIs                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  Duffel API      │  │  MercadoPago     │               │
│  │  (Flights)       │  │  (Payments)      │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19, TypeScript, Tailwind CSS, Vite | SPA with PWA support |
| **Backend** | Python 3.12, FastAPI, Celery | API + async task processing |
| **Database** | Supabase (PostgreSQL) | Auth, data storage, RLS |
| **Flights** | Duffel API (NDC) | Real-time airline offers |
| **Payments** | MercadoPago | Subscriptions & billing |
| **Notifications** | Telegram Bot, WhatsApp (Whapi), Resend | Multi-channel alerts |
| **Scraping** | Playwright + Stealth | Anti-bot web scraping |
| **Deploy** | Render (API) + Vercel (Frontend) | Cloud infrastructure |

## Features

### Price Monitoring
- **MercadoLibre**: Hybrid scraper with multi-identity spoofing (Desktop/iPhone)
- **Airbnb**: Playwright-based listing scraper with currency detection
- **Generic URLs**: JSON-LD, meta tags, CSS selectors, regex fallback
- **Price History**: Track price trends over time with charts
- **Anomaly Detection**: Identify price errors vs. historical average

### Flight Search
- **Duffel API**: Direct NDC integration for real-time flight offers
- **12-month search**: Automatic date range generation
- **Currency conversion**: USD → ARS using DolarAPI (Tarjeta rate)
- **Deal scoring**: Identify below-market prices

### Alert System
- **Multi-channel**: Email (Resend), Telegram, WhatsApp
- **Smart cooldown**: Prevents alert spam (30-min default)
- **Configurable rules**: Below price, above price, % drop, consecutive drops
- **Push notifications**: PWA web push via VAPID

### User Management
- **Auth**: Supabase Auth with email verification
- **Plans**: Starter (free) and Pro ($9/mes)
- **Billing**: MercadoPago checkout with IPN webhook
- **Profiles**: Telegram binding, WhatsApp number, report preferences

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+ (for frontend)
- Supabase account
- Duffel API key (for flights)

### Installation

```bash
# Clone
git clone https://github.com/vazquez-alejandro/howlify.git
cd howlify

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Frontend
cd frontend-react
npm install
```

### Configuration

```bash
# Copy env template
cp .env.example .env

# Fill in your credentials
# Required: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
# Optional: DUFFEL_ACCESS_TOKEN, TELEGRAM_TOKEN, MP_ACCESS_TOKEN
```

### Running

```bash
# Backend API
HOWLIFY_MODE=api python -m uvicorn howlify.api.main:app --reload --port 8000

# Celery Worker (background tasks)
celery -A howlify.celery_app worker --loglevel=info

# Celery Beat (scheduler)
celery -A howlify.celery_app beat --loglevel=info

# Frontend
cd frontend-react && npm run dev
```

### Production

```bash
# Docker
docker build -t howlify .
docker run -p 8000:8000 howlify

# Or use Render Blueprint
render deploy
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/health/detailed` | Detailed health with DB check |
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/signup` | User registration |
| GET | `/api/cazas` | List user hunts |
| POST | `/api/cazas` | Create new hunt |
| POST | `/api/hunt/{id}` | Execute single hunt |
| POST | `/api/hunt/all` | Execute all user hunts |
| GET | `/api/history/{id}` | Price history for hunt |
| GET | `/api/predict/{id}` | Price prediction |
| POST | `/api/mp/create-preference` | Create MP checkout |
| POST | `/api/mp/webhook` | MP IPN webhook |

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

## Project Structure

```
howlify/
├── howlify/
│   ├── api/
│   │   └── main.py          # FastAPI application
│   ├── celery_app.py        # Celery configuration
│   └── tasks.py             # Background tasks
├── scraper/
│   ├── scraper_pro.py       # Main scraper dispatcher
│   ├── generic.py           # Generic URL scraper
│   ├── airbnb.py            # Airbnb scraper
│   └── despegar.py          # Flight scraper (Duffel)
├── services/
│   ├── notification_service.py  # Email, Telegram, WhatsApp
│   ├── alerts_service.py        # Alert logic & dedup
│   └── database_service.py      # DB operations
├── engine/
│   ├── engine.py            # Alert rule evaluation
│   └── worker.py            # Standalone worker (legacy)
├── auth/
│   ├── supabase_client.py   # Supabase initialization
│   └── auth_supabase.py     # Auth helpers
├── utils/
│   ├── logic.py             # Shared utilities
│   ├── proxy.py             # Proxy management
│   └── logger.py            # Structured logging
├── frontend-react/          # React SPA (Vite + Tailwind)
├── tests/                   # pytest test suite
├── Dockerfile               # Container build
├── render.yaml              # Render Blueprint
└── requirements.txt         # Python dependencies
```

## Environment Variables

See [`.env.example`](.env.example) for all required and optional variables.

## License

Private - All rights reserved.

## Author

Alejandro Vazquez
