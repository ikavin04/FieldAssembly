-- FieldVoice Database Schema
-- Run against a PostgreSQL database to create all tables.

-- ============================================================
-- Equipment
-- ============================================================
CREATE TABLE IF NOT EXISTS equipment (
    id              SERIAL PRIMARY KEY,
    asset_code      VARCHAR(50)  UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    equipment_type  VARCHAR(50)  NOT NULL,
    location        VARCHAR(200),
    description     TEXT,
    operating_limits JSONB       DEFAULT '{}'::jsonb,
    required_inspection_fields JSONB DEFAULT '[]'::jsonb,
    created_at      TIMESTAMP    DEFAULT NOW(),
    updated_at      TIMESTAMP    DEFAULT NOW()
);

-- ============================================================
-- Inspections
-- ============================================================
CREATE TABLE IF NOT EXISTS inspections (
    id              SERIAL PRIMARY KEY,
    equipment_id    INTEGER      NOT NULL REFERENCES equipment(id),
    status          VARCHAR(20)  NOT NULL DEFAULT 'started',
    inspection_type VARCHAR(50),
    started_at      TIMESTAMP    DEFAULT NOW(),
    completed_at    TIMESTAMP,
    summary         TEXT,
    created_at      TIMESTAMP    DEFAULT NOW(),
    updated_at      TIMESTAMP    DEFAULT NOW()
);

-- ============================================================
-- Observations (with evidence)
-- ============================================================
CREATE TABLE IF NOT EXISTS observations (
    id               SERIAL PRIMARY KEY,
    inspection_id    INTEGER      NOT NULL REFERENCES inspections(id),
    field_name       VARCHAR(100) NOT NULL,
    value            VARCHAR(200),
    unit             VARCHAR(50),
    evidence_text    TEXT,
    source_timestamp REAL,
    confidence       REAL,
    created_at       TIMESTAMP    DEFAULT NOW()
);

-- ============================================================
-- Maintenance Tickets
-- ============================================================
CREATE TABLE IF NOT EXISTS maintenance_tickets (
    id              SERIAL PRIMARY KEY,
    inspection_id   INTEGER      NOT NULL REFERENCES inspections(id),
    equipment_id    INTEGER      NOT NULL REFERENCES equipment(id),
    issue           TEXT         NOT NULL,
    priority        VARCHAR(20)  NOT NULL DEFAULT 'medium',
    status          VARCHAR(20)  NOT NULL DEFAULT 'open',
    created_at      TIMESTAMP    DEFAULT NOW(),
    updated_at      TIMESTAMP    DEFAULT NOW()
);

-- ============================================================
-- Safety Alerts
-- ============================================================
CREATE TABLE IF NOT EXISTS safety_alerts (
    id              SERIAL PRIMARY KEY,
    inspection_id   INTEGER      NOT NULL REFERENCES inspections(id),
    equipment_id    INTEGER      NOT NULL REFERENCES equipment(id),
    hazard          TEXT         NOT NULL,
    severity        VARCHAR(20)  NOT NULL DEFAULT 'medium',
    evidence_text   TEXT,
    status          VARCHAR(20)  NOT NULL DEFAULT 'open',
    created_at      TIMESTAMP    DEFAULT NOW(),
    resolved_at     TIMESTAMP
);
