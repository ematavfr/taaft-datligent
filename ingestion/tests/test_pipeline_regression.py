"""
Pipeline regression tests — verify the full ingest flow (parse → scrape → enrich)
produces correct counts, categories, and field shapes.
All network I/O (httpx, Anthropic) is stubbed; no real credentials needed.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Stub the anthropic package before any ingestion module imports it
_anthropic_stub = MagicMock()
sys.modules.setdefault("anthropic", _anthropic_stub)

sys.path.insert(0, str(Path(__file__).parent.parent))

from html_parser import parse_taaft_html

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ── Expected output from sample_newsletter.html ─────────────────────────────
EXPECTED_TOOLS = [
    ("OpenAI Launches GPT-5", "Breaking News"),
    ("Google DeepMind Reveals AlphaFold 4", "Breaking News"),
    ("PromptWizard", "Coming in Hot"),
    ("DataLens", "AI Finds"),
]
EXPECTED_PROMPT = ("Brand Identity Architect", "Prompt of the Day")
EXPECTED_TOTAL = len(EXPECTED_TOOLS) + 1  # 5


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_fixture() -> str:
    return (FIXTURES_DIR / "sample_newsletter.html").read_text()


def tools(items):
    return [i for i in items if i["item_type"] == "tool"]


def prompts(items):
    return [i for i in items if i["item_type"] == "prompt"]


def _fake_enrichment(item: dict) -> dict:
    """Return a deterministic enrichment stub without calling Claude."""
    return {
        "description_fr": f"[FR] {item['description'][:80]}",
        "tags": ["ai", "automation"],
        "pricing": "freemium",
    }


async def _fake_scrape_item(item: dict, timeout: float = 10.0) -> dict:
    """Simulate scraper: set real_url and empty scraped data without HTTP calls."""
    item["real_url"] = item["url"].replace("beehiiv.com", "example-tool.com")
    item["scraped"] = {
        "meta_description": f"Tool page for {item['title']}",
        "body_text": "",
        "pricing_hint": "",
    }
    return item


# ── Parser regression ─────────────────────────────────────────────────────────

class TestParserRegression:
    def setup_method(self):
        self.html = load_fixture()
        self.items = parse_taaft_html(self.html)

    def test_total_item_count(self):
        assert len(self.items) == EXPECTED_TOTAL, (
            f"Expected {EXPECTED_TOTAL} items, got {len(self.items)}: "
            f"{[i['title'] for i in self.items]}"
        )

    def test_tool_count(self):
        assert len(tools(self.items)) == len(EXPECTED_TOOLS)

    def test_exactly_one_prompt(self):
        assert len(prompts(self.items)) == 1

    def test_tool_categories(self):
        by_title = {i["title"]: i["category"] for i in tools(self.items)}
        for title, expected_cat in EXPECTED_TOOLS:
            assert by_title.get(title) == expected_cat, (
                f"'{title}': expected category '{expected_cat}', got '{by_title.get(title)}'"
            )

    def test_prompt_title_and_category(self):
        p = prompts(self.items)[0]
        assert p["title"] == EXPECTED_PROMPT[0]
        assert p["category"] == EXPECTED_PROMPT[1]

    def test_prompt_item_type(self):
        p = prompts(self.items)[0]
        assert p["item_type"] == "prompt"

    def test_all_tools_item_type(self):
        for item in tools(self.items):
            assert item["item_type"] == "tool", f"'{item['title']}' should be item_type=tool"

    def test_all_items_have_url(self):
        for item in self.items:
            assert item.get("url", "").startswith("https://"), (
                f"'{item['title']}' has no valid URL"
            )

    def test_all_items_have_description(self):
        for item in self.items:
            assert len(item.get("description", "")) > 5, (
                f"'{item['title']}' has empty description"
            )

    def test_breaking_news_count(self):
        bn = [i for i in self.items if i["category"] == "Breaking News"]
        assert len(bn) == 2

    def test_no_boilerplate_titles(self):
        titles_lower = [i["title"].lower() for i in self.items]
        bad = {"view and copy today's full prompt", "click here", "prompt of the day",
               "view on web", "if you'd rather"}
        for title in titles_lower:
            assert title not in bad, f"Boilerplate title captured: '{title}'"

    def test_no_duplicate_urls(self):
        urls = [i["url"] for i in self.items]
        assert len(urls) == len(set(urls)), "Duplicate URLs found"


# ── Scraper integration (no HTTP) ─────────────────────────────────────────────

class TestScraperIntegration:
    def test_scrape_items_adds_real_url(self):
        from scraper import scrape_items
        items = parse_taaft_html(load_fixture())

        async def fake_resolve(url, timeout=10.0):
            return url.replace("beehiiv.com", "toolpage.com")

        with patch("scraper.resolve_url", new=fake_resolve):
            with patch("scraper.scrape_tool_page", new=AsyncMock(return_value={})):
                result = asyncio.run(scrape_items(items))

        assert all("real_url" in i for i in result), "All items must have real_url after scraping"
        assert all("scraped" in i for i in result), "All items must have scraped dict after scraping"

    def test_scrape_item_graceful_failure(self):
        """resolve_url catches network errors internally and returns the original URL."""
        from scraper import resolve_url
        item_url = "https://link.mail.beehiiv.com/test"

        # Simulate httpx raising inside resolve_url by patching httpx.AsyncClient
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(side_effect=Exception("network error"))
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scraper.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(resolve_url(item_url))

        assert result == item_url, "On network failure resolve_url returns the original URL"


# ── Enrichment integration (no Claude API) ───────────────────────────────────

class TestEnrichmentIntegration:
    def _make_item(self, title="Test Tool", description="An AI tool"):
        return {
            "title": title,
            "url": "https://example.com",
            "description": description,
            "category": "AI Finds",
            "item_type": "tool",
            "scraped": {},
        }

    def _make_mock_client(self, response_json: str):
        fake_response = MagicMock()
        fake_response.content = [MagicMock(type="text", text=response_json)]
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=fake_response)
        return mock_client

    def test_enrich_items_adds_required_fields(self):
        import enrichment
        # Reset singleton so our mock_client is picked up
        enrichment._client = self._make_mock_client(
            '{"description_fr":"FR desc","tags":["ai"],"pricing":"free"}'
        )
        try:
            items = [self._make_item("Tool A"), self._make_item("Tool B")]
            result = asyncio.run(enrichment.enrich_items(items))
        finally:
            enrichment._client = None

        assert len(result) == 2
        for item in result:
            assert "description_fr" in item, f"'{item['title']}' missing description_fr"
            assert isinstance(item["tags"], list) and len(item["tags"]) > 0
            assert item["pricing"] in {"free", "freemium", "paid", "open-source", "unknown"}

    def test_enrich_fallback_on_api_error(self):
        """On repeated API failure the item must still have default fields."""
        import enrichment

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API down"))
        enrichment._client = mock_client
        try:
            item = self._make_item()
            result = asyncio.run(enrichment.extract_metadata(item))
        finally:
            enrichment._client = None

        assert result["description_fr"] == item["description"]
        assert result["tags"] == ["AI"]
        assert result["pricing"] == "unknown"

    def test_build_user_content_includes_scraped_data(self):
        from enrichment import _build_user_content

        item = {
            "title": "MyTool",
            "description": "A great tool",
            "scraped": {
                "meta_description": "Best tool ever",
                "pricing_hint": "$9/mo",
                "body_text": "Feature A Feature B",
            },
        }
        content = _build_user_content(item)

        assert "MyTool" in content
        assert "A great tool" in content
        assert "Best tool ever" in content
        assert "$9/mo" in content

    def test_build_user_content_handles_missing_scraped(self):
        from enrichment import _build_user_content

        item = {"title": "MinimalTool", "description": "Brief desc", "scraped": {}}
        content = _build_user_content(item)
        assert "MinimalTool" in content
        assert "Brief desc" in content


# ── Full pipeline end-to-end (parse + scrape stub + enrich stub) ──────────────

class TestFullPipeline:
    """
    Simulate run_ingestion without email/DB/network.
    Verifies that the three pipeline stages compose correctly and produce
    the expected item shapes.
    """

    def test_parse_scrape_enrich_produces_correct_output(self):
        html = load_fixture()
        parsed = parse_taaft_html(html)

        # Stage 2: scrape (stubbed)
        scraped = asyncio.run(_fake_scrape_items(parsed))

        # Stage 3: enrich (stubbed)
        enriched = asyncio.run(_fake_enrich_items(scraped))

        assert len(enriched) == EXPECTED_TOTAL

        # All items have every field the DB writer and frontend expect
        required = {"title", "url", "real_url", "description", "description_fr",
                    "category", "item_type", "tags", "pricing"}
        for item in enriched:
            missing = required - item.keys()
            assert not missing, f"'{item['title']}' missing: {missing}"

        # Categories preserved through scrape + enrich
        categories = {i["category"] for i in enriched}
        assert "Prompt of the Day" in categories
        assert "Breaking News" in categories

        # Prompt of the Day item has correct type
        pot_items = [i for i in enriched if i["category"] == "Prompt of the Day"]
        assert len(pot_items) == 1
        assert pot_items[0]["item_type"] == "prompt"

        # Pricing is always a valid enum value
        valid_pricing = {"free", "freemium", "paid", "open-source", "unknown"}
        for item in enriched:
            assert item["pricing"] in valid_pricing, (
                f"'{item['title']}' has invalid pricing: {item['pricing']!r}"
            )


async def _fake_scrape_items(items: list) -> list:
    return [await _fake_scrape_item(dict(i)) for i in items]


async def _fake_enrich_items(items: list) -> list:
    for item in items:
        meta = _fake_enrichment(item)
        item["description_fr"] = meta["description_fr"]
        item["tags"] = meta["tags"]
        item["pricing"] = meta["pricing"]
    return items
