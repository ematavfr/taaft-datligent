import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from html_parser import parse_taaft_html

# ── Helpers ──────────────────────────────────────────────────────────────────

def tools(items):
    return [i for i in items if i["item_type"] == "tool"]


def prompts(items):
    return [i for i in items if i["item_type"] == "prompt"]


def all_titles(items):
    return [i["title"].lower() for i in items]


# ── Tool extraction ───────────────────────────────────────────────────────────

def test_tools_are_extracted(sample_newsletter_html):
    items = parse_taaft_html(sample_newsletter_html)
    assert len(tools(items)) >= 3


def test_tool_sections_assigned_correctly(sample_newsletter_html):
    items = parse_taaft_html(sample_newsletter_html)
    by_cat = {i["title"]: i["category"] for i in tools(items)}
    assert by_cat.get("OpenAI Launches GPT-5") == "Breaking News"
    assert by_cat.get("PromptWizard") == "Coming in Hot"
    assert by_cat.get("DataLens") == "AI Finds"


def test_tool_has_url_and_description(sample_newsletter_html):
    items = parse_taaft_html(sample_newsletter_html)
    for item in tools(items):
        assert item["url"].startswith("https://")
        assert len(item["description"]) > 0


# ── Prompt of the Day ─────────────────────────────────────────────────────────

def test_exactly_one_prompt(sample_newsletter_html):
    items = parse_taaft_html(sample_newsletter_html)
    assert len(prompts(items)) == 1


def test_prompt_category(sample_newsletter_html):
    items = parse_taaft_html(sample_newsletter_html)
    p = prompts(items)[0]
    assert p["category"] == "Prompt of the Day"


def test_prompt_title_is_actual_name(sample_newsletter_html):
    """Title must be the real prompt name, not the generic header or link text."""
    items = parse_taaft_html(sample_newsletter_html)
    p = prompts(items)[0]
    assert p["title"] == "Brand Identity Architect"


def test_prompt_title_not_generic_fallback(sample_newsletter_html):
    items = parse_taaft_html(sample_newsletter_html)
    p = prompts(items)[0]
    assert p["title"] != "Prompt of the Day"
    assert "view and copy" not in p["title"].lower()
    assert p["title"].lower() != "click here"


def test_prompt_description_is_substantive(sample_newsletter_html):
    items = parse_taaft_html(sample_newsletter_html)
    p = prompts(items)[0]
    assert len(p["description"]) > 30


# ── Boilerplate not captured ──────────────────────────────────────────────────

def test_view_and_copy_not_a_tool(sample_newsletter_html):
    """'View and copy today's full prompt' must never appear as a tool."""
    items = parse_taaft_html(sample_newsletter_html)
    assert not any("view and copy today" in t for t in all_titles(items))


def test_click_here_not_a_tool(sample_newsletter_html):
    """'click here' must never be captured as a tool title."""
    items = parse_taaft_html(sample_newsletter_html)
    assert "click here" not in all_titles(items)


def test_prompt_links_not_captured_as_tools(sample_newsletter_html):
    """Nothing from the Prompt of the Day section should appear in the tools list."""
    items = parse_taaft_html(sample_newsletter_html)
    prompt_url = prompts(items)[0]["url"]
    tool_urls = [i["url"] for i in tools(items)]
    assert prompt_url not in tool_urls
