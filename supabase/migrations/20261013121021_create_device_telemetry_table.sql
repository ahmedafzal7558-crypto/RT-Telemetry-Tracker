/*
# Create device_telemetry table for IoT Telemetry Processing Engine

## Purpose
Stores telemetry readings from IoT hardware devices. Each row represents a single
telemetry snapshot sent by a device at a point in time.

1. New Tables
- `device_telemetry`
  - `id` (bigserial, primary key) — auto-incrementing row identifier
  - `device_id` (text, not null) — unique identifier of the hardware device
  - `cpu_utilization` (double precision, not null) — CPU usage percentage (0.0–100.0)
  - `memory_usage` (double precision, not null) — memory usage percentage (0.0–100.0)
  - `ping_latency_ms` (integer, not null) — network ping latency in milliseconds
  - `timestamp` (timestamptz, not null) — UTC timestamp of the reading

2. Indexes
- `idx_device_telemetry_device_id` on `device_id` — speeds up per-device lookups
- `idx_device_telemetry_device_timestamp` on `(device_id, timestamp DESC)` — composite
  descending index for efficient historical range queries per device
- `idx_device_telemetry_timestamp` on `timestamp` — for cross-device time-range queries

3. Security
- Enable RLS on `device_telemetry`.
- This is a single-tenant IoT ingestion backend with no sign-in screen; the API
  service role handles access. Policies allow anon + authenticated CRUD so the
  anon-key client and the FastAPI backend (using the service role / anon key)
  can both read and write telemetry data.
*/