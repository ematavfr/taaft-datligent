import schedule
import time
import datetime
import asyncio
import os
import sys
from ingest_taaft import main as run_taaft_ingestion

# Configuration
SCHEDULE_TIME = os.environ.get("SCHEDULE_TIME", "08:30")
# Optional flag to run ingestion immediately on startup
RUN_ON_STARTUP = os.environ.get("RUN_ON_STARTUP", "true").lower() == "true"

def job():
    print(f"[{datetime.datetime.now()}] Starting scheduled TAAFT ingestion...")
    try:
        asyncio.run(run_taaft_ingestion())
        print(f"[{datetime.datetime.now()}] Scheduled TAAFT ingestion completed successfully.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Error during scheduled ingestion: {e}")

def main():
    print(f"Starting TAAFT Ingestion Scheduler. Frequency: Daily at {SCHEDULE_TIME}")
    
    if RUN_ON_STARTUP:
        print("Running initial ingestion on startup...")
        job()

    schedule.every().day.at(SCHEDULE_TIME).do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
