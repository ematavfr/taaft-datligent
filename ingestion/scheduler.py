import asyncio
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from ingest_taaft import main as run_taaft_ingestion

SCHEDULE_TIME = os.environ.get("SCHEDULE_TIME", "08:30")
RUN_ON_STARTUP = os.environ.get("RUN_ON_STARTUP", "true").lower() == "true"


async def job():
    logger.info("Starting scheduled TAAFT ingestion...")
    try:
        await run_taaft_ingestion()
        logger.info("Scheduled TAAFT ingestion completed")
    except Exception as e:
        logger.error(f"Scheduled ingestion failed: {e}")


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
        misfire_grace_time=3600,  # still run if missed by up to 1 hour
        coalesce=True,            # skip duplicate runs if scheduler was paused
        max_instances=1,
    )
    scheduler.start()
    logger.info(f"Scheduler running — next run at {SCHEDULE_TIME} UTC")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
