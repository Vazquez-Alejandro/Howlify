# 🛠 Roadmap Howlify

## ✅ Completado

### Google Sheets
- ✅ Exportar tablas a CSV/Excel — ya implementado.
- ✅ Exportación directa a Google Sheets vía API — endpoint POST /api/export/sheets.
- ✅ Botón "📤 Exportar" en dashboard Monitor — frontend React.
- ✅ Autenticación OAuth para Google Sheets (alternativa a Service Account bloqueada por Google Cloud).
- ✅ Token y credenciales en Secret Files de Render.

### Frontend
- ✅ Dashboard Monitor con ranking horizontal, bordes visibles, full-width.
- ✅ Mis Cacerías y Perfil a ancho completo.
- ✅ Botón descargar evidencia en modal de capturas.
- ✅ SPA React servido desde FastAPI en ruta `/`.

### Tests
- ✅ Tests de engine (11 tests para last_check, frecuencias, bloque de tiempo).

### Seguridad
- ✅ Rotación de keys de Supabase.
- ✅ Fix URL hardcodeada de Supabase en `mercadolibre_monitor.py`.

## 📈 Fases de escalado

### Fase 0 — Actual (todo free, $0/mes)
| Servicio | Plan | Rol |
|----------|------|-----|
| Render | Free | Web API + 2 workers (se duerme a los 15 min) |
| Supabase | Free | BD PostgreSQL + Auth |
| Upstash Redis | Free | Celery broker |
| cron-job.org | Free | Disparador periódico |
| Resend | Free | 100 emails/día |

**Problemas:** cold start (~30s), 512MB RAM compartida, workers compiten por recursos.

### Fase 1 — Mínimo pago (~$15/mes)
| Servicio | Plan | Costo | Cambio |
|----------|------|-------|--------|
| Render (web) | **Starter** | **$7/mes** | Sin sleeps, 1GB RAM, dominio custom |
| Supabase | Free | $0 | Sigue igual |
| Upstash | Free | $0 | Sigue igual |
| cron-job.org | Free | $0 | Sigue igual |
| Resend | Free | $0 | 100 emails/día |

**Cómo migrar:**
1. En Render Dashboard, upgrade web service a **Starter ($7/mes)**.
2. Opcional: unificar web + worker en un solo proceso para ahorrar (usar `HOWLIFY_MODE=api` y correr Celery worker en segundo plano o en un thread).
3. Configurar dominio personalizado en Render (Settings → Custom Domain).

### Fase 2 — Completo (~$30-40/mes)
| Servicio | Plan | Costo |
|----------|------|-------|
| Render (web) | Starter | $7/mes |
| Render (worker) | Starter | $7/mes |
| Supabase | **Pro** | **$25/mes** |
| Upstash | Free/Pro ($0-$5) | $0 |
| cron-job.org | Free | $0 |
| Resend | Free/Growth ($0-$10) | $0 |

**Mejoras:**
- Worker separado → no compite con web por RAM.
- Supabase Pro → 8GB BD, 100k usuarios, 50GB ancho de banda, Point-in-time recovery.
- Upstash Pro opcional si Redis necesita más conexiones.
- Resend Growth ($10/mes) si necesitás más de 100 emails/día.

### Fase 3 — Escalado horizontal (futuro, +$100/mes)
- Render → migrar a **Fly.io** o **Railway** para más control.
- Supabase Pro → **Supabase Team** o **PostgreSQL gestionado** (Neon, RDS).
- Agregar CDN (Cloudflare) para assets estáticos.
- Cache Redis en edge (Upstash Global).

## ✅ Pre-lanzamiento checklist

### 1. Landing page pública
- [x] Hero section con value prop
- [x] Features / cómo funciona
- [x] Pricing con planes reales (Starter $9, Pro $15, Reseller $39, Monitor $79)
- [x] CTA "Probar 7 días gratis"
- [x] Footer con links

### 2. Stripe + planes con límites
- [ ] Stripe Checkout para suscripciones
- [ ] Webhooks de Stripe → actualizar plan en Supabase
- [ ] Bloquear features según plan (máx cacerías, etc.)
- [ ] Dashboard de billing (cancelar, cambiar plan)

### 3. Onboarding tutorial
- [ ] Tooltips guiados al primer login
- [ ] Paso a paso: crear cacería → ver monitor → interpretar alertas

### 4. Errores amigables
- [ ] Traducir errores técnicos a mensajes de usuario
- [ ] Toast con acciones (reintentar, contactar soporte)
- [ ] Página de error 404/500 personalizada

### 5. Términos y privacidad
- [ ] Templates + personalizar para Howlify
- [ ] Link en footer y registro

## 📈 Fases de escalado
