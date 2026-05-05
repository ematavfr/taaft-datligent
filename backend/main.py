import os
from contextlib import asynccontextmanager
from datetime import date
from typing import AsyncGenerator, List, Optional

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db:5432/taaft")
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3002,http://localhost:5173").split(",")
]

pool: asyncpg.Pool = None  # type: ignore[assignment]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    logger.info("DB pool ready (min=2, max=10)")
    yield
    await pool.close()
    logger.info("DB pool closed")


app = FastAPI(title="TAAFT API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


class Item(BaseModel):
    id: int
    title: str
    url: str
    real_url: Optional[str] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    category: Optional[str] = None
    item_type: str
    tags: List[str] = []
    pricing: Optional[str] = None
    publication_date: date


@app.get("/items", response_model=List[Item])
async def get_items(
    target_date: Optional[date] = None,
    tag: List[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    query = "SELECT * FROM items"
    params: list = []
    where_clauses: list = []

    if target_date:
        where_clauses.append(f"publication_date = ${len(params) + 1}")
        params.append(target_date)

    if tag:
        where_clauses.append(f"tags && ${len(params) + 1}")
        params.append(tag)

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += f" ORDER BY id DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    return [dict(row) for row in rows]


@app.get("/dates")
async def get_available_dates():
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT publication_date FROM items ORDER BY publication_date DESC"
        )
    return [row["publication_date"] for row in rows]


@app.get("/tags")
async def get_all_tags():
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT unnest(tags) AS tag FROM items ORDER BY tag"
        )
    return [row["tag"] for row in rows]


@app.get("/search")
async def search_items(
    q: str = Query(..., min_length=2),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    pattern = f"%{q}%"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM items
               WHERE title ILIKE $1 OR description ILIKE $1 OR description_fr ILIKE $1
               ORDER BY publication_date DESC, id DESC
               LIMIT $2 OFFSET $3""",
            pattern, limit, offset,
        )
    return [dict(row) for row in rows]


@app.get("/metrics")
async def metrics():
    async with pool.acquire() as conn:
        total_items = await conn.fetchval("SELECT COUNT(*) FROM items")
        dates_count = await conn.fetchval("SELECT COUNT(DISTINCT publication_date) FROM items")
        try:
            last_run = await conn.fetchrow(
                "SELECT run_date, status, items_count, finished_at FROM ingestion_runs"
                " ORDER BY finished_at DESC LIMIT 1"
            )
            recent_failures = await conn.fetch(
                "SELECT run_date, status, error_message, finished_at FROM ingestion_runs"
                " WHERE status = 'failed' ORDER BY finished_at DESC LIMIT 5"
            )
        except Exception:
            last_run = None
            recent_failures = []

    return {
        "total_items": total_items,
        "dates_covered": dates_count,
        "last_ingestion": dict(last_run) if last_run else None,
        "recent_failures": [dict(r) for r in recent_failures],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
