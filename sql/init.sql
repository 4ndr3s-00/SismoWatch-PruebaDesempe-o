-- ==============================================================================
-- SismoWatch: Database Initialization Script
-- Architecture: Medallion (Raw -> Staging -> Curated + Quarantine)
-- ==============================================================================

-- 1. Create Distinct Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS quarantine;
CREATE SCHEMA IF NOT EXISTS audit;

-- 2. Raw Layer (Bronze): Inmutable Append-Only
CREATE TABLE IF NOT EXISTS raw.seismic_events_raw (
    raw_id BIGSERIAL PRIMARY KEY,
    source_id VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_id VARCHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_source_id ON raw.seismic_events_raw(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_ingested_at ON raw.seismic_events_raw(ingested_at);

-- 3. Staging Layer (Silver): Validated Schema & Types
CREATE TABLE IF NOT EXISTS staging.seismic_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,
    latitude NUMERIC(8, 4) NOT NULL,
    longitude NUMERIC(8, 4) NOT NULL,
    depth NUMERIC(8, 2) NOT NULL,
    magnitude NUMERIC(4, 2) NOT NULL,
    place VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'automatic',
    ingested_at TIMESTAMPTZ NOT NULL,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_id VARCHAR(64) NOT NULL
);

-- Temporary Staging table used for Spark JDBC Atomic Upserts
CREATE TABLE IF NOT EXISTS staging.temp_curated_events (
    event_id VARCHAR(64) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    latitude NUMERIC(8, 4) NOT NULL,
    longitude NUMERIC(8, 4) NOT NULL,
    depth NUMERIC(8, 2) NOT NULL,
    magnitude NUMERIC(4, 2) NOT NULL,
    place VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'reviewed',
    ingested_at TIMESTAMPTZ NOT NULL,
    run_id VARCHAR(64) NOT NULL
);

-- 4. Curated Layer (Gold): Analytics & AI Consumption (Unpartitioned Table)
CREATE TABLE IF NOT EXISTS curated.seismic_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,
    latitude NUMERIC(8, 4) NOT NULL,
    longitude NUMERIC(8, 4) NOT NULL,
    depth NUMERIC(8, 2) NOT NULL,
    magnitude NUMERIC(4, 2) NOT NULL,
    place VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'reviewed',
    ingested_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_curated_time_mag ON curated.seismic_events(event_time DESC, magnitude DESC);
CREATE INDEX IF NOT EXISTS idx_curated_geo ON curated.seismic_events(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_curated_updated_at ON curated.seismic_events(updated_at ASC);

-- 5. Lateral Quarantine Branch (Dead-Letter Store)
CREATE TABLE IF NOT EXISTS quarantine.rejected_events (
    rejection_id BIGSERIAL PRIMARY KEY,
    source_id VARCHAR(64),
    original_payload JSONB NOT NULL,
    failed_rule_code VARCHAR(64) NOT NULL,
    failed_rule_desc TEXT NOT NULL,
    pipeline_stage VARCHAR(32) NOT NULL, -- 'RAW_TO_STAGING' or 'STAGING_TO_CURATED'
    run_id VARCHAR(64) NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolution_status VARCHAR(32) NOT NULL DEFAULT 'PENDING'
);

CREATE INDEX IF NOT EXISTS idx_quarantine_stage_code ON quarantine.rejected_events(pipeline_stage, failed_rule_code);
CREATE INDEX IF NOT EXISTS idx_quarantine_run_id ON quarantine.rejected_events(run_id);

-- 6. Audit & Quality Metrics Table
CREATE TABLE IF NOT EXISTS audit.metrics_execution (
    metric_id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    execution_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    records_ingested INT NOT NULL DEFAULT 0,
    records_staged INT NOT NULL DEFAULT 0,
    records_curated INT NOT NULL DEFAULT 0,
    records_quarantined INT NOT NULL DEFAULT 0,
    quality_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    processing_latency_seconds NUMERIC(8, 2) NOT NULL DEFAULT 0.00,
    sla_met BOOLEAN NOT NULL DEFAULT TRUE
);

-- 7. Real-time PostgreSQL LISTEN / NOTIFY Function & Trigger
-- Only fires when substantive seismic values actually change
CREATE OR REPLACE FUNCTION curated.notify_seismic_event_change()
RETURNS TRIGGER AS $$
DECLARE
    payload JSON;
BEGIN
    IF (TG_OP = 'INSERT') OR 
       (TG_OP = 'UPDATE' AND (
            OLD.magnitude IS DISTINCT FROM NEW.magnitude OR
            OLD.depth IS DISTINCT FROM NEW.depth OR
            OLD.latitude IS DISTINCT FROM NEW.latitude OR
            OLD.longitude IS DISTINCT FROM NEW.longitude OR
            OLD.place IS DISTINCT FROM NEW.place
       )) THEN
        payload = json_build_object(
            'event_id', NEW.event_id,
            'action', TG_OP,
            'magnitude', NEW.magnitude,
            'place', NEW.place,
            'event_time', NEW.event_time,
            'updated_at', NEW.updated_at
        );
        -- Keep notify payload lightweight (< 8000 bytes)
        PERFORM pg_notify('curated_event_channel', payload::text);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_curated_change ON curated.seismic_events;
CREATE TRIGGER trg_notify_curated_change
AFTER INSERT OR UPDATE ON curated.seismic_events
FOR EACH ROW EXECUTE FUNCTION curated.notify_seismic_event_change();

-- 8. Least-Privilege Security Roles
-- Application reader for AI Agent and Dashboard (Strictly Curated Schema)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_curated_reader') THEN
        CREATE ROLE app_curated_reader WITH LOGIN PASSWORD 'CuratedReaderPass123!';
    END IF;
END
$$;

-- Grant permissions to read-only app user
GRANT USAGE ON SCHEMA curated TO app_curated_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA curated TO app_curated_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT SELECT ON TABLES TO app_curated_reader;

-- Explicitly revoke access to raw, staging and quarantine schemas
REVOKE ALL ON SCHEMA raw FROM app_curated_reader;
REVOKE ALL ON SCHEMA staging FROM app_curated_reader;
REVOKE ALL ON SCHEMA quarantine FROM app_curated_reader;
REVOKE ALL ON SCHEMA audit FROM app_curated_reader;
