import datetime
import os
import shutil
import time

import psycopg2
from loguru import logger

UPDATES_DIR = "/app/updates"
PROCESSED_DIR = "/app/processed"
DB_URL = os.environ.get("DATABASE_URL")
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "90"))


def get_db_connection():
    try:
        return psycopg2.connect(DB_URL)
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return None


def process_files():
    if not os.path.exists(UPDATES_DIR):
        logger.warning(f"Updates directory not found: {UPDATES_DIR}")
        return

    files = sorted(f for f in os.listdir(UPDATES_DIR) if f.endswith(".sql"))
    if not files:
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        for filename in files:
            filepath = os.path.join(UPDATES_DIR, filename)
            logger.info(f"Processing {filename}")
            try:
                with open(filepath) as f:
                    sql_content = f.read()
                cursor.execute(sql_content)
                conn.commit()
                logger.info(f"Applied {filename}")
                shutil.move(filepath, os.path.join(PROCESSED_DIR, filename))
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to apply {filename}: {e}")
                shutil.move(filepath, os.path.join(PROCESSED_DIR, filename + ".failed"))
        cursor.close()
    except Exception as e:
        logger.error(f"Unexpected error in process_files: {e}")
    finally:
        conn.close()


def purge_old_processed_files():
    """Remove files from processed/ older than RETENTION_DAYS days."""
    if not os.path.exists(PROCESSED_DIR):
        return
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=RETENTION_DAYS)).timestamp()
    purged = 0
    for filename in os.listdir(PROCESSED_DIR):
        filepath = os.path.join(PROCESSED_DIR, filename)
        try:
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                purged += 1
        except Exception as e:
            logger.warning(f"Could not purge {filename}: {e}")
    if purged:
        logger.info(f"Purged {purged} files older than {RETENTION_DAYS} days")


def main():
    logger.info(f"DB Updater starting (retention={RETENTION_DAYS}d)...")
    os.makedirs(UPDATES_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    cycle = 0
    while True:
        process_files()
        if cycle % 48 == 0:  # purge once per day (48 × 30min cycles)
            purge_old_processed_files()
        cycle += 1
        time.sleep(1800)


if __name__ == "__main__":
    main()
