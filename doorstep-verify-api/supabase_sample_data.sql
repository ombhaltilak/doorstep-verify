-- ═══════════════════════════════════════════════════════════════════════════
-- DoorStep — Sample Test Deliveries
-- Run in Supabase → SQL Editor to load test data.
-- Replace coordinates with your actual delivery addresses before testing.
-- Use the Admin Portal (📍 GPS button) to capture real coordinates accurately.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Clear existing test deliveries ───────────────────────────────────────
DELETE FROM deliveries
WHERE tracking_id IN ('IMGTEST01', 'VIDTEST01', 'TEST03');

-- ── Insert sample deliveries ──────────────────────────────────────────────
-- NOTE: Replace expected_lat/expected_lng with the actual front door
--       coordinates for your test location.

INSERT INTO deliveries
  (tracking_id, customer_name, address, driver_id, expected_lat, expected_lng, status)
VALUES
  (
    'IMGTEST01',
    'James Carter',
    '847 Oak Street, Chicago, IL 60601',
    'driver01',
    0.0000,
    0.0000,
    'pending'
  ),
  (
    'VIDTEST01',
    'Sarah Mitchell',
    '1234 Maple Avenue, Chicago, IL 60602',
    'driver01',
    0.0000,
    0.0000,
    'pending'
  ),
  (
    'TEST03',
    'Robert Hayes',
    '500 Michigan Avenue, Chicago, IL 60611',
    'driver01',
    0.0000,
    0.0000,
    'pending'
  );

-- ── Reset existing deliveries to pending (use instead of re-inserting) ────
-- Uncomment this block to reset without deleting and re-inserting:
/*
UPDATE deliveries
SET
  status       = 'pending',
  verified     = NULL,
  checks       = NULL,
  file_url     = NULL,
  proof_hash   = NULL,
  timestamp    = NULL,
  media_type   = NULL,
  gps_lat      = NULL,
  gps_lng      = NULL,
  gps_accuracy = NULL
WHERE tracking_id IN ('IMGTEST01', 'VIDTEST01', 'TEST03');
*/

-- ── Verify ────────────────────────────────────────────────────────────────
SELECT tracking_id, customer_name, driver_id, status, expected_lat, expected_lng
FROM deliveries
ORDER BY created_at DESC;
