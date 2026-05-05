-- Database schema for TAAFT items
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    description TEXT,
    description_fr TEXT,
    category TEXT,
    item_type TEXT DEFAULT ‘tool’,
    notion_id TEXT,
    tags TEXT[] DEFAULT ‘{}’,
    real_url TEXT,
    pricing TEXT DEFAULT ‘unknown’,
    publication_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for date-based retrieval
CREATE INDEX IF NOT EXISTS idx_publication_date ON items(publication_date);

-- Ingestion run history (created here for new installs; also created by ingestor at startup)
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id            SERIAL PRIMARY KEY,
    run_date      DATE      NOT NULL,
    status        TEXT      NOT NULL,
    items_count   INTEGER   DEFAULT 0,
    error_message TEXT,
    started_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at   TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_date ON ingestion_runs(run_date);
