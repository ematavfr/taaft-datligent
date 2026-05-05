import datetime
import email
import imaplib
from email.header import decode_header

from loguru import logger

IMAP_SERVER = "imap.gmail.com"


def connect_gmail(user: str, password: str):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(user, password)
    return mail


def get_newsletter_by_date(mail, target_date: datetime.date, subject_filter: str = None):
    """Search TAAFT newsletter for a specific date across Gmail folders."""
    for folder in ["INBOX", '"[Gmail]/All Mail"', '"[Gmail]/Tous les messages"']:
        try:
            status, _ = mail.select(folder)
            if status != "OK":
                continue

            status, response = mail.search(None, '(FROM "hi@mail.theresanaiforthat.com")')
            if status != "OK":
                continue

            msg_ids = response[0].split()
            if not msg_ids:
                continue

            for msg_id in reversed(msg_ids[-30:]):
                status, data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(data[0][1])

                if subject_filter:
                    raw = msg.get("Subject", "")
                    decoded = "".join(
                        part.decode(enc or "utf-8", errors="ignore") if isinstance(part, bytes) else part
                        for part, enc in decode_header(raw)
                    )
                    if subject_filter.lower() not in decoded.lower():
                        continue

                date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                if date_tuple:
                    local_date = datetime.datetime.fromtimestamp(
                        email.utils.mktime_tz(date_tuple)
                    ).date()
                    if local_date in (target_date, target_date - datetime.timedelta(days=1)):
                        logger.info(f"Newsletter found for {target_date} in {folder}")
                        return msg
        except Exception as e:
            logger.error(f"Error searching {folder}: {e}")

    return None


def extract_html(msg) -> str:
    """Extract the HTML body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return part.get_payload(decode=True).decode()
    return msg.get_payload(decode=True).decode()
