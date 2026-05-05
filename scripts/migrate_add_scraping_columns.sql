-- Migration: add real_url and pricing columns to items table
-- Run once against an existing database: psql $DATABASE_URL -f scripts/migrate_add_scraping_columns.sql

ALTER TABLE items ADD COLUMN IF NOT EXISTS real_url TEXT;
ALTER TABLE items ADD COLUMN IF NOT EXISTS pricing TEXT DEFAULT 'unknown';

-- Backfill real_url with the existing beehiiv url for rows that don't have one yet
UPDATE items SET real_url = url WHERE real_url IS NULL;
