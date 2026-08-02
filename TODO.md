# Howlify — TODO de Producción

## Bugs Corregidos (Audit 2026-07-31)

### Backend
1. **TestNotificationRequest `canal` vs `channel`** — Frontend sends `{ canal }` but backend expected `{ channel }`. Fixed: backend now accepts both via `get_channel()` method.
2. **`enviar_whatsapp` wrong args in engine.py** — Was passing a dict instead of string. Fixed: now passes formatted string.
3. **`save_price_history` string `"now()"`** — Inserted literal string instead of timestamp. Fixed: now uses `datetime.now(timezone.utc).isoformat()`.
4. **`list_cazas` / `hunt_all` / `export_csv` hardcoded "starter"** — All three endpoints always passed `"starter"` plan. Fixed: now queries user's actual plan from profiles.
5. **CazaCard edit modal missing "grande"** — Only offered "piso" and "descuento". Fixed: added "Grandes ofertas" option.
6. **CSV export bypassed API client token refresh** — Used raw `fetch()`. Fixed: added `exportCsv()` to api client with proper refresh logic.
7. **Frontend error handling missing** — `loadCazas`, `handleHuntAll`, `handleDelete` swallowed errors silently. Fixed: added error feedback via toast.
8. **`Caza` interface missing `frecuencia`** — Backend returns it, frontend type didn't have it. Fixed: added to interface.

## Pendiente

### Crítico
- [ ] **Rotar credenciales** — `.env` tiene tokens reales (Telegram, Whapi, Resend, Supabase, SMTP, Redis, Duffel, ScraperAPI). Aunque `.env` no está en git, las credenciales están expuestas. Regenerar todos los tokens.
- [ ] **Configurar dominio en Resend** — `RESEND_FROM_EMAIL` usa `onboarding@resend.dev` (dominio de prueba). Configurar dominio propio en Resend para emails profesionales.
- [ ] **MP_WEBHOOK_SECRET vacío** — MercadoPago webhook no verifica firmas. Configurar en Render dashboard.

### Importante
- [ ] **In-memory rate limiter** — Se resetea al reiniciar el contenedor en Render. Migrar a Redis (Upstash ya está configurado) o aceptar que el rate limit se pierde.
- [ ] **AuthContext dual token state** — `api/client.ts` actualiza tokens en localStorage pero el React state de AuthContext queda desincronizado. Considerar refactoring a un solo owner de tokens.
- [ ] **ProtectedRoute no verifica validez del token** — Solo chequea `!!token`, no si expiró. El usuario entra al dashboard y ve errores en lugar de ser redirigido.
- [ ] **`useRates` cache sin expiración** — Los tipos de cambio se cachean para toda la sesión SPA. Si el usuario deja abierto el tab, muestra cotizaciones obsoletas.

### Menor
- [ ] **Email hardcoded 3 veces** — `howlify.app@gmail.com` aparece en LandingPage, TermsModal y DashboardPage. Centralizar en env var.
- [ ] **Tipo de producto no se envía** — Tabs "producto/vuelo/alojamiento" en NewCazaForm son solo UI, el valor no se envía al backend. Remover tabs o conectar al backend.
- [ ] **`refreshSession` en AuthContext es dead code** — Nadie la llama. El refresh lo maneja `api/client.ts`. Considerar eliminar.
- [ ] **Playwright en Docker** — El Dockerfile instala Playwright + Chromium (~500MB). Considerar solo instalarlo cuando `OH_PLAYWRIGHT=1`.
- [ ] **Streamlit en requirements.txt** — `streamlit==1.54.0` no se usa en producción. Remover del requirements.
- [ ] **`howlify/__main__.py` referencia `app.py`** — El módulo __main__ tiene `run_streamlit()` que busca `app.py` que no existe. Limpiar código muerto.

### Infra
- [ ] **3 servicios en Render** — API + Worker + Beat. Verificar que el worker y beat estén corriendo correctamente.
- [ ] **Celery beat schedule cada 60s** — `vigilar_ofertas_task` corre cada minuto. Verificar que no exceda los límites de Render (free tier tiene 750h/mes).
- [ ] **Docker image size** — Python 3.12 + Playwright + Chromium es grande. Considerar multi-stage build o solo instalar Chromium cuando sea necesario.
