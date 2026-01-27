import sys
import datetime
import asyncio
import re
import os

# Ensure we can import ingest_taaft
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ingest_taaft import run_ingestion, connect_gmail

async def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_ingest_taaft.py <YYYY-MM-DD_YYYY-MM-DD>")
        print("Example: python batch_ingest_taaft.py 2026-01-01_2026-01-10")
        return

    arg = sys.argv[1]
    
    # regex to find dates in YYYY-MM-DD format
    dates_found = re.findall(r"(\d{4}-\d{2}-\d{2})", arg)
    
    if len(dates_found) < 2:
        print(f"Error: Could not find two dates in '{arg}'.")
        print("Expected format: YYYY-MM-DD_YYYY-MM-DD (or any separator between two YYYY-MM-DD dates)")
        return
        
    try:
        start_date = datetime.datetime.strptime(dates_found[0], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(dates_found[1], "%Y-%m-%d").date()
    except ValueError as e:
        print(f"Error parsing dates: {e}")
        return
        
    if start_date > end_date:
        print(f"Error: Start date ({start_date}) is after end date ({end_date}).")
        return
        
    print(f"🚀 Starting batch processing from {start_date} to {end_date}...")
    
    mail = connect_gmail()
    try:
        current_date = start_date
        while current_date <= end_date:
            print(f"\n--- Processing Date: {current_date} ---")
            await run_ingestion(current_date, mail=mail)
            current_date += datetime.timedelta(days=1)
    except Exception as e:
        print(f"Batch execution error: {e}")
    finally:
        print("\nLogging out from Gmail...")
        mail.logout()
        print("Batch process finished.")

if __name__ == "__main__":
    asyncio.run(main())
