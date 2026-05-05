import asyncio
import re

import httpx
from bs4 import BeautifulSoup
from loguru import logger

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_PRICING_RE = re.compile(
    r"\b(free\s+trial|freemium|free\s+forever|free\s+plan|open[- ]source|"
    r"per\s+month|\/mo|per\s+user|contact\s+sales|enterprise|starting\s+at|"
    r"\$\d+|\€\d+)\b",
    re.IGNORECASE,
)


async def resolve_url(beehiiv_url: str, timeout: float = 10.0) -> str:
    """Follow the beehiiv redirect chain and return the final destination URL."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=timeout, headers=_HEADERS
        ) as client:
            response = await client.get(beehiiv_url)
            final = str(response.url)
            if "beehiiv.com" in final:
                return beehiiv_url
            return final
    except Exception as e:
        logger.warning(f"URL resolve failed for {beehiiv_url[:80]}: {e}")
        return beehiiv_url


async def scrape_tool_page(url: str, timeout: float = 10.0) -> dict:
    """Fetch a tool page and extract key text content for enrichment."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=timeout, headers=_HEADERS
        ) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return {}

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        meta = soup.find("meta", {"name": "description"}) or soup.find(
            "meta", {"property": "og:description"}
        )
        meta_description = (meta.get("content", "") if meta else "").strip()[:400]

        body_text = soup.get_text(separator=" ", strip=True)
        pricing_hits = _PRICING_RE.findall(body_text)
        pricing_hint = ", ".join(dict.fromkeys(h.lower() for h in pricing_hits[:6]))

        return {
            "meta_description": meta_description,
            "body_text": body_text[:2000],
            "pricing_hint": pricing_hint,
        }
    except Exception as e:
        logger.warning(f"Scrape failed for {url[:80]}: {e}")
        return {}


async def scrape_item(item: dict, timeout: float = 10.0) -> dict:
    """Resolve real URL and scrape content for a single item (mutates item in-place)."""
    beehiiv_url = item.get("url", "")
    real_url = await resolve_url(beehiiv_url, timeout=timeout)
    item["real_url"] = real_url

    if real_url != beehiiv_url and "beehiiv.com" not in real_url:
        item["scraped"] = await scrape_tool_page(real_url, timeout=timeout)
    else:
        item["scraped"] = {}

    return item


async def scrape_items(items: list, concurrency: int = 5, timeout: float = 10.0) -> list:
    """Resolve + scrape all items in parallel, bounded by concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def _guarded(item):
        async with semaphore:
            return await scrape_item(item, timeout=timeout)

    return list(await asyncio.gather(*(_guarded(i) for i in items)))
