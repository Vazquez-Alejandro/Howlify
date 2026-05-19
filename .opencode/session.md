# Sesión 19/05/2026

## ✅ Hecho
- Landing page pública: hero, features, pricing real (Starter $9, Pro $15, Reseller $39, Monitor $79), "7 días gratis"
- Login movido a `/login`, landing en `/`
- Vistas de cacerías y perfil a ancho completo
- Botón descargar evidencia en modal
- Exportar a Google Sheets funcionando (OAuth)
- Deploy en Render exitoso (fix uvicorn)
- Roadmap actualizado con fases de escalado y checklist pre-lanzamiento

## ⏭️ Próximo paso (mañana)
**Stripe + planes con límites** — implementar suscripciones:
1. Stripe Checkout para cada plan
2. Webhooks de Stripe → actualizar plan en Supabase
3. Bloquear features según plan (máx cacerías, etc.)
4. Dashboard de billing (cancelar, cambiar plan)

## Pendientes después de Stripe
- Onboarding tutorial
- Errores amigables en frontend
- Términos y privacidad
