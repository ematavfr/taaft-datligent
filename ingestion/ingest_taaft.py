import asyncio
import datetime
import os
import sys

from db_writer import write_to_db
from dotenv import load_dotenv
from email_client import connect_gmail, extract_html, get_newsletter_by_date
from enrichment import enrich_items
from html_parser import parse_taaft_html
from loguru import logger
from monitoring import ensure_monitoring_table, record_ingestion_run, send_alert
from notion_utils import NotionSync
from scraper import scrape_items

if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("../.env"):
    load_dotenv("../.env")
else:
    load_dotenv()

EMAIL_USER = os.environ.get("GMAIL_USER", "").strip('"')
EMAIL_PASS = os.environ.get("GMAIL_PASS", "").strip('"')
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
DB_URL = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")


async def run_ingestion(target_date: datetime.date, mail=None, subject_filter: str = None):
    logger.info(f"Ingestion started for {target_date}")
    started_at = datetime.datetime.utcnow()
    status = "failed"
    items_count = 0
    error_message = None
    close_mail = not mail

    try:
        if not mail:
            mail = connect_gmail(EMAIL_USER, EMAIL_PASS)

        msg = get_newsletter_by_date(mail, target_date, subject_filter)
        if not msg:
            status = "no_newsletter"
            logger.warning(f"No newsletter found for {target_date}")
            send_alert(f"⚠️ TAAFT: no newsletter found for *{target_date}*")
            return

        html_content = extract_html(msg)
        items = parse_taaft_html(html_content)
        logger.info(f"Parsed {len(items)} items")

        if not items:
            status = "no_newsletter"
            send_alert(f"⚠️ TAAFT: newsletter found for *{target_date}* but 0 items extracted")
            return

        logger.info(f"Scraping {len(items)} tool pages...")
        items = await scrape_items(items)

        logger.info(f"Enriching {len(items)} items...")
        final_items = await enrich_items(items)

        written = await write_to_db(final_items, target_date, DB_URL)
        items_count = written
        status = "success"

        if NOTION_TOKEN and NOTION_DATABASE_ID:
            notion = NotionSync(NOTION_TOKEN)
            for item in final_items:
                if item.get("item_type") == "prompt":
                    logger.info(f"Syncing prompt to Notion: {item['title']}")
                    try:
                        notion.create_prompt_page(
                            NOTION_DATABASE_ID,
                            item["title"],
                            item["url"],
                            item["description_fr"],
                            item["description"],
                            item["tags"],
                            target_date.strftime("%Y-%m-%d"),
                        )
                    except Exception as e:
                        logger.error(f"Notion sync error: {e}")
        else:
            logger.info("Notion sync skipped: credentials not configured")

        logger.info(f"Ingestion complete for {target_date} — {items_count} items")

    except Exception as e:
        error_message = str(e)
        logger.exception(f"Ingestion failed for {target_date}: {e}")
        send_alert(f"🚨 TAAFT ingestion *FAILED* for *{target_date}*\n```{e}```")
        raise

    finally:
        if close_mail and mail:
            try:
                mail.logout()
            except Exception:
                pass
        await record_ingestion_run(
            DB_URL, target_date, status, items_count, error_message, started_at
        )


async def main():
    await ensure_monitoring_table(DB_URL)

    target_date = datetime.date.today()
    if len(sys.argv) > 1:
        try:
            target_date = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Invalid date: {sys.argv[1]}. Expected YYYY-MM-DD")
            return
    subject_filter = sys.argv[2] if len(sys.argv) > 2 else None
    await run_ingestion(target_date, subject_filter=subject_filter)


if __name__ == "__main__":
    asyncio.run(main())
