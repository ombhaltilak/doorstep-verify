-- ═══════════════════════════════════════════════════════════════════════════
-- DoorStep — Proof of Delivery
-- Run this ONCE in Supabase → SQL Editor → Run
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. Deliveries table ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS deliveries (
  id             SERIAL PRIMARY KEY,
  tracking_id    TEXT NOT NULL,
  driver_id      TEXT,
  customer_name  TEXT,
  address        TEXT,
  front_door_w3w TEXT,
  expected_lat   FLOAT,
  expected_lng   FLOAT,
  status         TEXT DEFAULT 'pending',
  verified       BOOLEAN,
  media_type     TEXT,
  file_url       TEXT,
  proof_hash     TEXT,
  gps_lat        FLOAT,
  gps_lng        FLOAT,
  gps_accuracy   FLOAT,
  timestamp      TIMESTAMPTZ,
  checks         JSONB,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── 2. Unique constraint (required for upsert) ────────────────────────────
ALTER TABLE deliveries
  ADD CONSTRAINT IF NOT EXISTS deliveries_tracking_id_key UNIQUE (tracking_id);

-- ── 3. Indexes for fast lookups ───────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_driver_status ON deliveries(driver_id, status);
CREATE INDEX IF NOT EXISTS idx_tracking      ON deliveries(tracking_id);

-- ── 4. Disable Row Level Security (API uses service key — RLS not needed) ─
ALTER TABLE deliveries DISABLE ROW LEVEL SECURITY;

-- ── 5. Storage bucket for proof files ────────────────────────────────────
INSERT INTO storage.buckets (id, name, public)
VALUES ('proof-files', 'proof-files', true)
ON CONFLICT DO NOTHING;
