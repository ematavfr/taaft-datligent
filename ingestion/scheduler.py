import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ingest_taaft import main as run_taaft_ingestion
from loguru import logger

SCHEDULE_TIME = os.environ.get("SCHEDULE_TIME", "08:30")
RUN_ON_STARTUP = os.environ.get("RUN_ON_STARTUP", "true").lower() == "true"
PROCESSED_DIR = Path(os.environ.get("PROCESSED_DIR", "/data/processed"))
PURGE_DAYS = int(os.environ.get("PURGE_DAYS", "90"))


async def job():
    logger.info("Starting scheduled TAAFT ingestion...")
    try:
        await run_taaft_ingestion()
        logger.info("Scheduled TAAFT ingestion completed")
    except Exception as e:
        logger.error(f"Scheduled ingestion failed: {e}")


def purge_processed_files() -> None:
    """Delete .sql/.failed files in PROCESSED_DIR older than PURGE_DAYS days."""
    if not PROCESSED_DIR.is_dir():
        return
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=PURGE_DAYS)
    deleted = 0
    for f in PROCESSED_DIR.iterdir():
        if f.suffix in (".sql", ".failed") and f.is_file():
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                f.unlink()
                deleted += 1
    if deleted:
        logger.info(f"Purged {deleted} processed file(s) older than {PURGE_DAYS} days")


async def main():
    hour, minute = SCHEDULE_TIME.split(":")
    logger.info(f"TAAFT Scheduler starting — daily at {SCHEDULE_TIME} UTC")

    if RUN_ON_STARTUP:
        logger.info("Running ingestion on startup...")
        await job()

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        job,
        CronTrigger(hour=int(hour), minute=int(minute), timezone="UTC"),
        id="daily_ingestion",
        misfire_grace_time=3600,
        coalesce=True,
        max_instances=1,
    )
    # Purge old processed files once a week (Sunday 03:00 UTC)
    scheduler.add_job(
        purge_processed_files,
        CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="UTC"),
        id="weekly_purge",
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(f"Scheduler running — ingestion at {SCHEDULE_TIME} UTC, purge every Sunday 03:00")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
