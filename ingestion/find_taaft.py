import os
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("../.env"):
    load_dotenv("../.env")

# Configuration
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = os.environ.get("GMAIL_USER", "").strip('"')
EMAIL_PASS = os.environ.get("GMAIL_PASS", "").strip('"')

def connect_gmail():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    return mail

def find_taaft_emails(mail):
    mail.select("inbox")
    # Search for TAAFT in subject or anywhere
    status, messages = mail.search(None, 'SUBJECT "TAAFT"')
    if status != "OK" or not messages[0]:
        print("No TAAFT emails found in inbox. Searching [Gmail]/All Mail...")
        mail.select('"[Gmail]/All Mail"')
        status, messages = mail.search(None, 'SUBJECT "TAAFT"')
        if status != "OK" or not messages[0]:
            return []

    email_ids = messages[0].split()
    results = []
    
    # Get the last 5
    for eid in email_ids[-5:]:
        status, msg_data = mail.fetch(eid, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                date = msg["date"]
                sender = msg["from"]
                results.append(f"Date: {date} | Subject: {subject} | From: {sender}")
    return results

if __name__ == "__main__":
    mail = connect_gmail()
    emails = find_taaft_emails(mail)
    for e in emails:
        print(e)
