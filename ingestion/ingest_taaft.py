import os
import imaplib
import email
import datetime
import requests
import sys
import json
import asyncio
import re
from bs4 import BeautifulSoup
from email.header import decode_header
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from notion_utils import NotionSync

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("../.env"):
    load_dotenv("../.env")
else:
    load_dotenv()

# Configuration
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = os.environ.get("GMAIL_USER", "").strip('"')
EMAIL_PASS = os.environ.get("GMAIL_PASS", "").strip('"')
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "updates"))

# Standardized LLM / MCP Config
BASE_URL = os.environ.get("BASE_URL", "http://host.docker.internal:11434/v1").strip('"')
# Fallback for local run outside docker
if "host.docker.internal" in BASE_URL:
    try:
        import socket
        socket.gethostbyname("host.docker.internal")
    except socket.gaierror:
        BASE_URL = BASE_URL.replace("host.docker.internal", "localhost")

MODEL_NAME = os.environ.get("MODEL_NAME", "qwen3:latest").strip('"')
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# Initialize LLM
llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key="nope",
    base_url=BASE_URL,
)

def connect_gmail():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    return mail

def get_newsletter_by_date(mail, target_date):
    mail.select("inbox")
    date_str = target_date.strftime("%d-%b-%Y")
    # Sender and Subject updated based on analysis
    search_criteria = f'(FROM "hi@mail.theresanaiforthat.com" ON "{date_str}")'
    print(f"Searching with criteria: {search_criteria}")
    
    status, messages = mail.search(None, search_criteria)
    if status != "OK" or not messages[0]:
        print("Not found in inbox, searching All Mail...")
        # Support both English and French localized Gmail folder names
        for folder in ['"[Gmail]/All Mail"', '"[Gmail]/Tous les messages"']:
            status, _ = mail.select(folder)
            if status == "OK":
                break
        
        status, messages = mail.search(None, search_criteria)
        if status != "OK" or not messages[0]:
            return None

    latest_email_id = messages[0].split()[-1]
    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            return msg
    return None

async def extract_metadata(text):
    """Translates text to French and extracts tags using LLM."""
    if not text:
        return {"description_fr": "", "tags": []}
    
    prompt = f"""
    Analyse la description suivante et :
    1. Traduis-la intégralement en français.
    2. Génère une liste de 3 à 5 tags pertinents (en anglais technique uniquement, ex: "AI", "SaaS", "DevTools").
    
    Réponds uniquement au format JSON : {{"description_fr": "...", "tags": ["tag1", "tag2"]}}
    
    Description: {text}
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(llm.invoke, prompt)
            raw_response = response.content.strip()
            # Handle potential markdown backticks
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:-3].strip()
            elif raw_response.startswith("```"):
                raw_response = raw_response[3:-3].strip()
            
            data = json.loads(raw_response)
            return {
                "description_fr": data.get("description_fr", text),
                "tags": data.get("tags", ["AI"])
            }
        except Exception as e:
            print(f"Extraction error (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
    
    return {"description_fr": text, "tags": ["AI"]}

def parse_taaft_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove styles and scripts
    for s in soup(['style', 'script']):
        s.decompose()
        
    items = []
    sections = [
        "Breaking News", "Coming in Hot", "Today’s Spotlight", 
        "AI Finds", "Notable AIs", "Open Source Finds", "Prompt of the Day"
    ]
    
    for section_name in sections:
        # Find the header tag
        header = soup.find(lambda t: t.name in ['b', 'strong', 'span', 'p'] and section_name in t.get_text())
        if not header:
            continue
            
        print(f"Parsing section: {section_name}")
        
        # Logic varies by section
        if section_name == "Prompt of the Day":
            # Prompt of the Day has a specific structure
            title_tag = header.find_next(['span', 'p', 'b'])
            if title_tag:
                title = title_tag.get_text(strip=True)
                notion_link = None
                description = ""
                
                # Search for Notion link and description
                curr = title_tag
                for _ in range(20):
                    curr = curr.find_next(['a', 'p', 'span'])
                    if not curr: break
                    
                    if "click here" in curr.get_text().lower() and curr.name == 'a':
                        notion_link = curr.get('href')
                    
                    # Description is usually a longer block of text
                    t = curr.get_text(strip=True)
                    if len(t) > 100 and not description and not curr.find('a'):
                        description = t
                
                if title and notion_link:
                    items.append({
                        "title": title,
                        "url": notion_link,
                        "description": description,
                        "category": section_name,
                        "item_type": "prompt"
                    })
        else:
            # Regular sections: look for links followed by descriptions
            curr = header
            section_items_count = 0
            # Search ahead until we hit the next section or certain limit
            for _ in range(50):
                curr = curr.find_next(['a', 'p', 'span', 'b', 'strong'])
                if not curr: break
                
                # If we hit another section header, stop
                txt = curr.get_text(strip=True)
                if any(s in txt for s in sections if s != section_name) and curr.name in ['b', 'strong', 'span']:
                    break
                
                # Look for potential item title (link)
                if curr.name == 'a' and len(txt) > 2 and "beehiiv.com" in curr.get('href', ''):
                    # Exclude meta links
                    if any(exclude in txt.lower() for exclude in ["unsubscribe", "preferences", "sponsor", "gear", "feedback"]):
                        continue
                        
                    title = txt
                    url = curr.get('href')
                    
                    # Look for next text block (description)
                    description = ""
                    desc_tag = curr.find_next(['p', 'span'])
                    if desc_tag:
                        description = desc_tag.get_text(strip=True)
                    
                    if title and url and len(description) > 10:
                        items.append({
                            "title": title,
                            "url": url,
                            "description": description,
                            "category": section_name,
                            "item_type": "tool"
                        })
                        section_items_count += 1
                        # If we found 5 items in a section, that's usually enough/limit
                        if section_items_count >= 10: break
    
    return items

def generate_sql(items, target_date):
    filename = f"taaft-{target_date.strftime('%Y-%m-%d')}.sql"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(filepath, "w") as f:
        f.write(f"DELETE FROM items WHERE publication_date = '{target_date.strftime('%Y-%m-%d')}';\n\n")
        
        # Deduplicate items by URL
        seen_urls = set()
        for item in items:
            if item['url'] in seen_urls: continue
            seen_urls.add(item['url'])
            
            title = item['title'].replace("'", "''")
            url = item['url'].replace("'", "''")
            description = item.get('description', '').replace("'", "''")
            description_fr = item.get('description_fr', '').replace("'", "''")
            category = item.get('category', 'General').replace("'", "''")
            item_type = item.get('item_type', 'tool').replace("'", "''")
            tags = item.get('tags', ["AI"])
            tags_str = "{" + ",".join(['"' + t.replace("'", "''") + '"' for t in tags]) + "}"
            pub_date = target_date.strftime('%Y-%m-%d')

            sql = f"INSERT INTO items (title, url, description, description_fr, category, item_type, tags, publication_date) VALUES ('{title}', '{url}', '{description}', '{description_fr}', '{category}', '{item_type}', '{tags_str}', '{pub_date}') ON CONFLICT (url) DO UPDATE SET title = EXCLUDED.title, description = EXCLUDED.description, description_fr = EXCLUDED.description_fr, category = EXCLUDED.category, item_type = EXCLUDED.item_type, tags = EXCLUDED.tags, publication_date = EXCLUDED.publication_date;"
            f.write(sql + "\n")
            
    print(f"Generated {filepath}")

async def run_ingestion(target_date, mail=None):
    print(f"Processing TAAFT for {target_date}...")
    
    close_mail = False
    if not mail:
        mail = connect_gmail()
        close_mail = True
        
    msg = get_newsletter_by_date(mail, target_date)
    
    if not msg:
        print(f"No newsletter found for {target_date}.")
        if close_mail: mail.logout()
        return

    html_content = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_content = part.get_payload(decode=True).decode()
                break
    else:
        html_content = msg.get_payload(decode=True).decode()

    items = parse_taaft_html(html_content)
    print(f"Extracted {len(items)} items.")
    
    # Process translations sequentially to avoid overwhelming LLM
    final_items = []
    for item in items:
        print(f"Extracting metadata (translation + tags) for: {item['title']}")
        metadata = await extract_metadata(item['description'])
        item['description_fr'] = metadata['description_fr']
        item['tags'] = metadata['tags']
        final_items.append(item)
    
    if final_items:
        generate_sql(final_items, target_date)
        
        # Sync prompts to Notion
        if NOTION_TOKEN and NOTION_DATABASE_ID:
            notion = NotionSync(NOTION_TOKEN)
            for item in final_items:
                if item.get('item_type') == 'prompt':
                    print(f"Syncing prompt to Notion: {item['title']}")
                    notion.create_prompt_page(
                        NOTION_DATABASE_ID,
                        item['title'],
                        item['url'],
                        item['description_fr'],
                        item['description'],
                        item['tags'],
                        target_date.strftime('%Y-%m-%d')
                    )
        else:
            print("Notion sync skipped: credentials missing.")
    else:
        print(f"No items to process for {target_date}.")
        
    if close_mail:
        mail.logout()

async def main():
    target_date = datetime.date.today()
    if len(sys.argv) > 1:
        try:
            target_date = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format: {sys.argv[1]}. Use YYYY-MM-DD")
            return
            
    await run_ingestion(target_date)

if __name__ == "__main__":
    asyncio.run(main())
