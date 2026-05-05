import datetime
import os

import asyncpg
import requests
from loguru import logger

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id           SERIAL PRIMARY KEY,
    run_date     DATE      NOT NULL,
    status       TEXT      NOT NULL,   -- 'success' | 'no_newsletter' | 'failed'
    items_count  INTEGER   DEFAULT 0,
    error_message TEXT,
    started_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_date ON ingestion_runs(run_date);
"""


async def ensure_monitoring_table(db_url: str) -> None:
    """Create ingestion_runs table if it doesn't already exist (idempotent)."""
    if not db_url:
        return
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(_CREATE_TABLE_SQL)
        logger.debug("ingestion_runs table ready")
    finally:
        await conn.close()


async def record_ingestion_run(
    db_url: str,
    run_date: datetime.date,
    status: str,
    items_count: int = 0,
    error_message: str = None,
    started_at: datetime.datetime = None,
) -> None:
    """Insert a row in ingestion_runs. Silently skips if db_url is not set."""
    if not db_url:
        return
    finished_at = datetime.datetime.utcnow()
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(
            """INSERT INTO ingestion_runs
                   (run_date, status, items_count, error_message, started_at, finished_at)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            run_date,
            status,
            items_count,
            error_message,
            started_at or finished_at,
            finished_at,
        )
    except Exception as e:
        logger.error(f"Failed to record ingestion run: {e}")
    finally:
        await conn.close()


def send_alert(message: str) -> None:
    """Send a Slack webhook alert. No-op if SLACK_WEBHOOK_URL is not configured."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.debug("SLACK_WEBHOOK_URL not set — alert suppressed")
        return
    try:
        resp = requests.post(webhook_url, json={"text": message}, timeout=5)
        if resp.ok:
            logger.info("Alert sent to Slack")
        else:
            logger.warning(f"Slack returned HTTP {resp.status_code}")
    except Exception as e:
        logger.error(f"Slack alert failed: {e}")
