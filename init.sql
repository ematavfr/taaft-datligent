-- Database schema for TAAFT items
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    description TEXT, -- Original description
    description_fr TEXT, -- French translated description
    category TEXT, -- Breaking News, Coming in Hot, Today’s Spotlight, AI Finds, Notable AIs, Open Source Finds, Prompt of the Day
    item_type TEXT DEFAULT 'tool', -- 'tool' or 'prompt'
    notion_id TEXT, -- For Notion sync tracking
    tags TEXT[] DEFAULT '{}',
    publication_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for date-based retrieval
CREATE INDEX IF NOT EXISTS idx_publication_date ON items(publication_date);
