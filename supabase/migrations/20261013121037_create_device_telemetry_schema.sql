CREATE TABLE IF NOT EXISTS device_telemetry (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    cpu_utilization DOUBLE PRECISION NOT NULL,
    memory_usage DOUBLE PRECISION NOT NULL,
    ping_latency_ms INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_device_telemetry_device_id
    ON device_telemetry (device_id);

CREATE INDEX IF NOT EXISTS idx_device_telemetry_device_timestamp
    ON device_telemetry (device_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_device_telemetry_timestamp
    ON device_telemetry (timestamp);

ALTER TABLE device_telemetry ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_telemetry" ON device_telemetry;
CREATE POLICY "anon_select_telemetry"
    ON device_telemetry FOR SELECT
    TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_telemetry" ON device_telemetry;
CREATE POLICY "anon_insert_telemetry"
    ON device_telemetry FOR INSERT
    TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_telemetry" ON device_telemetry;
CREATE POLICY "anon_update_telemetry"
    ON device_telemetry FOR UPDATE
    TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_telemetry" ON device_telemetry;
CREATE POLICY "anon_delete_telemetry"
    ON device_telemetry FOR DELETE
    TO anon, authenticated USING (true);