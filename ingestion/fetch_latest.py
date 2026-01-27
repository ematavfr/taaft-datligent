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

def fetch_latest_taaft(mail):
    mail.select("inbox")
    status, messages = mail.search(None, '(FROM "hi@mail.theresanaiforthat.com")')
    if status != "OK" or not messages[0]:
        print("No TAAFT emails found.")
        return

    latest_id = messages[0].split()[-1]
    status, data = mail.fetch(latest_id, "(RFC822)")
    msg = email.message_from_bytes(data[0][1])
    
    subject, encoding = decode_header(msg["subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8")
        
    print(f"Latest TAAFT ID: {latest_id}")
    print(f"Date: {msg['date']}")
    print(f"Subject: {subject}")
    
    html_content = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_content = part.get_payload(decode=True).decode()
                break
    else:
        html_content = msg.get_payload(decode=True).decode()
        
    with open("latest_taaft.html", "w") as f:
        f.write(html_content)
    print("HTML saved to latest_taaft.html")

if __name__ == "__main__":
    mail = connect_gmail()
    fetch_latest_taaft(mail)
