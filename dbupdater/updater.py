import os
import time
import shutil
import psycopg2
from psycopg2 import sql

UPDATES_DIR = "/app/updates"
PROCESSED_DIR = "/app/processed"
DB_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def process_files():
    if not os.path.exists(UPDATES_DIR):
        print(f"Directory {UPDATES_DIR} does not exist.")
        return

    files = [f for f in os.listdir(UPDATES_DIR) if f.endswith(".sql")]
    if not files:
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        for filename in files:
            filepath = os.path.join(UPDATES_DIR, filename)
            print(f"Processing {filename}...")
            
            try:
                with open(filepath, "r") as f:
                    sql_content = f.read()
                
                cursor.execute(sql_content)
                conn.commit()
                print(f"Successfully executed {filename}")
                
                # Move to processed
                shutil.move(filepath, os.path.join(PROCESSED_DIR, filename))
                print(f"Moved {filename} to {PROCESSED_DIR}")
                
            except Exception as e:
                conn.rollback()
                print(f"Error processing {filename}: {e}")
                # Optional: Move to a 'failed' directory or rename? 
                # For now, leave it there or maybe rename to .failed to avoid infinite loop if it's a syntax error
                # Renaming to .failed
                shutil.move(filepath, os.path.join(PROCESSED_DIR, filename + ".failed"))
                print(f"Moved failed file {filename} to {PROCESSED_DIR} with .failed extension")

        cursor.close()
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        conn.close()

def main():
    print("Starting DB Updater Service...")
    # Ensure directories exist
    os.makedirs(UPDATES_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    while True:
        process_files()
        time.sleep(1800)

if __name__ == "__main__":
    main()
