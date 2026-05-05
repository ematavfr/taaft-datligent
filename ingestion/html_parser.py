import datetime
import re

from bs4 import BeautifulSoup
from loguru import logger

SECTION_MAP = {
    "Breaking News": "Breaking News",
    "The Latest AI Developments": "Breaking News",
    "Coming in Hot": "Coming in Hot",
    "AI Tools of the Day": "Coming in Hot",
    "Today's Spotlight": "Today's Spotlight",
    "AI Finds": "AI Finds",
    "Beyond the Feed": "AI Finds",
    "Open Source Finds": "Open Source Finds",
    "From the Source": "Open Source Finds",
    # Sentinel: stops tool capture when Prompt of the Day section begins
    "Prompt of the Day": "_PROMPT",
}

SKIP_TITLES = {
    "view on web", "subscribe", "read more", "share", "refer", "advertise",
    "click here", "here",
}

# Titles that start with these prefixes are also skipped (case-insensitive)
SKIP_TITLE_PREFIXES = (
    "view and copy today",
    "if you'd rather",
    "explore the collection",
)

SKIP_SOCIALS = ("twitter.com", "linkedin.com", "facebook.com", "instagram.com")

# Phrases that mark boilerplate rows inside the Prompt of the Day section
PROMPT_SKIP_PHRASES = (
    "important note",
    "view and copy today",
    "if you'd rather",
    "click the button",
    "explore the collection",
    "by taaft",
)


def parse_taaft_html(html_content: str) -> list:
    soup = BeautifulSoup(html_content, "html.parser")
    for el in soup(["style", "script"]):
        el.decompose()

    items: list = []
    current_section: str | None = None
    seen_urls: set = set()

    # ── Tool items ────────────────────────────────────────────────────────────
    for tr in soup.find_all("tr"):
        tr_text = tr.get_text(strip=True)
        if not tr_text:
            continue

        # Section header detection
        header_found = False
        for s_key, s_name in SECTION_MAP.items():
            if s_key in tr_text and len(tr_text) < 50:
                if current_section != s_name:
                    current_section = s_name
                    logger.debug(f"Section: {s_name}")
                header_found = True
                break

        # Stop capturing tools once we reach the Prompt of the Day section
        if header_found or not current_section or current_section == "_PROMPT":
            continue

        for link in tr.find_all("a", href=lambda x: x and "beehiiv.com" in x):
            url = link.get("href")
            if not url or url in seen_urls:
                continue

            title_tag = link.find(["b", "strong"]) or (
                link.parent and link.parent.find(["b", "strong"])
            )
            title = title_tag.get_text(strip=True) if title_tag else link.get_text(strip=True)

            if (
                not title
                or len(title) < 2
                or title.lower() in SKIP_TITLES
                or title.lower().startswith(SKIP_TITLE_PREFIXES)
                or any(s in url.lower() for s in SKIP_SOCIALS)
            ):
                continue

            description = tr_text.replace(title, "").strip()
            for s_name in SECTION_MAP.values():
                description = description.replace(s_name, "").strip()
            description = re.sub(r"^[•\-\:\s💬]+", "", description)

            items.append({
                "title": title,
                "url": url,
                "description": description or title,
                "category": current_section,
                "item_type": "tool",
            })
            seen_urls.add(url)

    # ── Prompt of the Day ─────────────────────────────────────────────────────
    prompt_header = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3", "h4", "h5", "h6", "b", "strong", "span", "div", "td"]
        and "Prompt of the Day" in tag.get_text(strip=True)
        and len(tag.get_text(strip=True)) < 30
    )

    if prompt_header:
        curr = prompt_header
        while curr and curr.name not in ["tr", "div"]:
            curr = curr.parent

        actual_title: str | None = None
        description = ""
        url = ""
        count = 0

        while curr and count < 25:
            curr = curr.find_next(["tr", "div"])
            if not curr:
                break
            count += 1
            row_text = curr.get_text(strip=True)
            if not row_text or len(row_text) < 3:
                continue
            if "Prompt of the Day" in row_text and len(row_text) < 30:
                continue

            # Always try to grab the beehiiv URL from any row in this block
            if not url:
                for a_tag in curr.find_all("a"):
                    href = a_tag.get("href", "")
                    if href and any(d in href for d in ["beehiiv.com", "theresanaiforthat.com"]):
                        url = href
                        break

            # Skip boilerplate rows (after extracting URL above)
            if any(phrase in row_text.lower() for phrase in PROMPT_SKIP_PHRASES):
                continue

            # First non-skip, reasonably short row → actual prompt title
            if actual_title is None and len(row_text) <= 120:
                bold = curr.find(["b", "strong"])
                candidate = (
                    bold.get_text(strip=True)
                    if bold and len(bold.get_text(strip=True)) > 3
                    else row_text
                )
                actual_title = candidate
                continue  # do not use the title row as the description

            # First substantial text after the title → description
            if not description and len(row_text) > 15:
                description = row_text

            if url and description and actual_title is not None:
                break

        title = actual_title if actual_title else "Prompt of the Day"

        if description or actual_title:
            existing = next(
                (i for i in items if i["url"] == url or (url and i["url"] in url)), None
            )
            if existing:
                existing["item_type"] = "prompt"
                existing["category"] = "Prompt of the Day"
                if title != "Prompt of the Day":
                    existing["title"] = title
                if len(description) > len(existing.get("description", "")):
                    existing["description"] = description
            else:
                items.append({
                    "title": title,
                    "url": url or f"https://theresanaiforthat.com/prompts/?date={datetime.date.today()}",
                    "description": description or title,
                    "category": "Prompt of the Day",
                    "item_type": "prompt",
                })
            logger.info(f"Prompt of the Day: {title}")
    else:
        logger.warning("Prompt of the Day header not found in newsletter")

    return items
