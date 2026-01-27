import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from datetime import date
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="TAAFT API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db:5432/taaft")

class Item(BaseModel):
    id: int
    title: str
    url: str
    description: Optional[str]
    description_fr: Optional[str]
    category: Optional[str]
    item_type: str
    tags: List[str] = []
    publication_date: date

async def get_db_conn():
    # Handle both DSN and separate params if needed, but asyncpg.connect(dsn) is standard
    return await asyncpg.connect(DATABASE_URL)

@app.get("/items", response_model=List[Item])
async def get_items(
    target_date: Optional[date] = None, 
    tag: List[str] = Query(None)
):
    conn = await get_db_conn()
    try:
        query = "SELECT * FROM items"
        params = []
        where_clauses = []
        
        if target_date:
            where_clauses.append(f"publication_date = ${len(params) + 1}")
            params.append(target_date)
            
        if tag and len(tag) > 0:
            # tag is a list, we want items that have ANY of these tags
            # Or if the user meant ALL, we would use <@ or other logic.
            # overlaps operator && checks if arrays have any common elements
            where_clauses.append(f"tags && ${len(params) + 1}")
            params.append(tag)
            
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY id DESC"
        
        if not target_date and not (tag and len(tag) > 0):
            query += " LIMIT 50"
            
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
    finally:
        await conn.close()

@app.get("/dates")
async def get_available_dates():
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("SELECT DISTINCT publication_date FROM items ORDER BY publication_date DESC")
        return [row['publication_date'] for row in rows]
    finally:
        await conn.close()

@app.get("/tags")
async def get_all_tags():
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("SELECT DISTINCT unnest(tags) as tag FROM items ORDER BY tag")
        return [row['tag'] for row in rows]
    finally:
        await conn.close()

@app.get("/health")
async def health():
    return {"status": "ok"}
