import datetime

import asyncpg
from loguru import logger


async def write_to_db(items: list, target_date: datetime.date, db_url: str) -> int:
    """Persist items to PostgreSQL using parameterised queries inside a transaction."""
    if not db_url:
        logger.warning("db_url not provided — items will not be persisted")
        return 0

    seen_urls: set = set()
    rows = []
    for item in items:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            rows.append(item)

    conn = await asyncpg.connect(db_url)
    written = 0
    try:
        async with conn.transaction():
            await conn.execute("DELETE FROM items WHERE publication_date = $1", target_date)
            for item in rows:
                await conn.execute(
                    """INSERT INTO items
                           (title, url, real_url, description, description_fr,
                            category, item_type, tags, pricing, publication_date)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                       ON CONFLICT (url) DO UPDATE SET
                           title            = EXCLUDED.title,
                           real_url         = EXCLUDED.real_url,
                           description      = EXCLUDED.description,
                           description_fr   = EXCLUDED.description_fr,
                           category         = EXCLUDED.category,
                           item_type        = EXCLUDED.item_type,
                           tags             = EXCLUDED.tags,
                           pricing          = EXCLUDED.pricing,
                           publication_date = EXCLUDED.publication_date""",
                    item["title"],
                    item["url"],
                    item.get("real_url") or item["url"],
                    item.get("description", ""),
                    item.get("description_fr", ""),
                    item.get("category", "General"),
                    item.get("item_type", "tool"),
                    item.get("tags", ["AI"]),
                    item.get("pricing", "unknown"),
                    target_date,
                )
                written += 1
        logger.info(f"Persisted {written} items for {target_date}")
    finally:
        await conn.close()
    return written
