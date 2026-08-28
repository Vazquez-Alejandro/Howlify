-- Howlify — Pivot revendedores
-- Agrega stock a price_history para detección de restock real.
-- Ejecutar en Supabase SQL Editor / Neon una vez.
ALTER TABLE price_history ADD COLUMN IF NOT EXISTS stock INTEGER;
CREATE INDEX IF NOT EXISTS idx_price_history_stock
  ON price_history (caza_id, checked_at DESC, stock);