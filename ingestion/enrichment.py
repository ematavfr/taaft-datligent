import asyncio
import json

import anthropic
from loguru import logger

_client: anthropic.AsyncAnthropic | None = None

_SYSTEM_PROMPT = (
    "You are a technical taxonomy assistant for AI tools. "
    "Given information about an AI tool (newsletter snippet and optionally a scraped webpage), you must:\n"
    "1. Write a concise French summary (maximum 150 characters).\n"
    "2. Generate 3 to 5 relevant technical tags in English (lowercase, no spaces).\n"
    "3. Classify the pricing tier as one of: free, freemium, paid, open-source, unknown.\n\n"
    "Reply with a JSON object only."
)

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "description_fr": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "pricing": {
            "type": "string",
            "enum": ["free", "freemium", "paid", "open-source", "unknown"],
        },
    },
    "required": ["description_fr", "tags", "pricing"],
    "additionalProperties": False,
}


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic()
    return _client


def _build_user_content(item: dict) -> str:
    parts = [f"Title: {item['title']}", f"Newsletter description: {item['description']}"]
    scraped = item.get("scraped", {})
    if scraped.get("meta_description"):
        parts.append(f"Page meta description: {scraped['meta_description']}")
    if scraped.get("pricing_hint"):
        parts.append(f"Pricing mentions found on page: {scraped['pricing_hint']}")
    if scraped.get("body_text"):
        parts.append(f"Page content (excerpt): {scraped['body_text'][:1000]}")
    return "\n".join(parts)


async def extract_metadata(item: dict) -> dict:
    """Translate to French, generate tags, and detect pricing tier via Claude API."""
    client = _get_client()
    user_content = _build_user_content(item)

    for attempt in range(3):
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=300,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
                output_config={"format": {"type": "json_schema", "schema": _OUTPUT_SCHEMA}},
            )
            text_block = next((b for b in response.content if b.type == "text"), None)
            if text_block:
                data = json.loads(text_block.text)
                return {
                    "description_fr": data.get("description_fr", item["description"]),
                    "tags": data.get("tags", ["AI"]),
                    "pricing": data.get("pricing", "unknown"),
                }
        except Exception as e:
            logger.warning(f"Metadata extraction attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2)

    return {"description_fr": item["description"], "tags": ["AI"], "pricing": "unknown"}


async def enrich_items(items: list, concurrency: int = 5) -> list:
    """Enrich all items with French descriptions, tags and pricing, bounded by concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def _enrich(item):
        async with semaphore:
            logger.debug(f"Enriching: {item['title']}")
            meta = await extract_metadata(item)
            item["description_fr"] = meta["description_fr"]
            item["tags"] = meta["tags"]
            item["pricing"] = meta["pricing"]
            return item

    return list(await asyncio.gather(*(_enrich(i) for i in items)))
