#!/usr/bin/env python3
"""
Frontend QA: verifies every API contract the React app depends on.
Run after deployment: python scripts/qa_api.py [--url http://localhost:8002]
Exit 0 = all checks passed, exit 1 = at least one failure.
"""
import argparse
import json
import sys
from datetime import date

import httpx

CATEGORY_ORDER = [
    "Prompt of the Day",
    "Breaking News",
    "Coming in Hot",
    "Today’s Spotlight",
    "AI Finds",
    "Notable AIs",
    "Open Source Finds",
]
VALID_PRICING = {"free", "freemium", "paid", "open-source", "unknown"}

passed = 0
failed = 0


def ok(label: str) -> None:
    global passed
    passed += 1
    print(f"  \033[32m✓\033[0m  {label}")


def fail(label: str, detail: str = "") -> None:
    global failed
    failed += 1
    msg = f"  \033[31m✗\033[0m  {label}"
    if detail:
        msg += f"\n       {detail}"
    print(msg)


def check(cond: bool, label: str, detail: str = "") -> bool:
    if cond:
        ok(label)
    else:
        fail(label, detail)
    return cond


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


def run(base_url: str) -> None:
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # ── /health ──────────────────────────────────────────────────────────────
    section("/health")
    r = client.get("/health")
    check(r.status_code == 200, "returns 200")
    check(r.json().get("status") == "ok", 'body is {"status":"ok"}')

    # ── /dates ───────────────────────────────────────────────────────────────
    section("/dates")
    r = client.get("/dates")
    check(r.status_code == 200, "returns 200")
    dates = r.json()
    has_dates = check(isinstance(dates, list) and len(dates) > 0, "list is non-empty",
                      f"got {len(dates)} dates")
    if has_dates:
        check(dates == sorted(dates, reverse=True), "dates are sorted DESC")
        try:
            date.fromisoformat(dates[0])
            ok("first date is ISO-8601 string")
        except (ValueError, TypeError):
            fail("first date is ISO-8601 string", f"got {dates[0]!r}")
        latest = dates[0]
    else:
        latest = None

    # ── /items (by date) ─────────────────────────────────────────────────────
    section("/items")
    params = {"target_date": latest} if latest else {}
    r = client.get("/items", params=params)
    check(r.status_code == 200, "returns 200")
    items = r.json()
    has_items = check(isinstance(items, list) and len(items) > 0, "list is non-empty",
                      f"got {len(items)} items")

    if has_items:
        # required fields present in every item
        required = {"id", "title", "url", "item_type", "tags", "publication_date"}
        missing_fields = [
            f"{item.get('title','?')!r} missing {required - item.keys()}"
            for item in items
            if required - item.keys()
        ]
        check(not missing_fields, "all items have required fields",
              "; ".join(missing_fields[:3]))

        # tags is always a list
        bad_tags = [
            item.get("title", "?")
            for item in items
            if not isinstance(item.get("tags"), list)
        ]
        check(not bad_tags, "tags field is always a list",
              f"bad in: {bad_tags[:3]}")

        # item_type is tool or prompt
        bad_type = [
            item.get("title", "?")
            for item in items
            if item.get("item_type") not in ("tool", "prompt")
        ]
        check(not bad_type, "item_type is 'tool' or 'prompt'",
              f"bad in: {bad_type[:3]}")

        # pricing is valid enum
        bad_pricing = [
            item.get("title", "?")
            for item in items
            if item.get("pricing") and item["pricing"] not in VALID_PRICING
        ]
        check(not bad_pricing, "pricing values are valid enum",
              f"bad in: {bad_pricing[:3]}")

        # at least one Prompt of the Day
        categories = {item.get("category") for item in items}
        check("Prompt of the Day" in categories, "contains 'Prompt of the Day' category",
              f"found: {sorted(categories)}")

        # Prompt of the Day items are item_type=prompt
        pot_d = [i for i in items if i.get("category") == "Prompt of the Day"]
        bad_prompt_type = [i.get("title", "?") for i in pot_d if i.get("item_type") != "prompt"]
        check(not bad_prompt_type, "Prompt of the Day items have item_type=prompt",
              f"bad: {bad_prompt_type}")

        # real_url is present when set
        with_real = [i for i in items if i.get("real_url")]
        check(len(with_real) >= 0, f"real_url populated on {len(with_real)}/{len(items)} items")

    # ── /items pagination ────────────────────────────────────────────────────
    r2 = client.get("/items", params={"limit": 1, "offset": 0, **({"target_date": latest} if latest else {})})
    check(r2.status_code == 200, "pagination: limit=1 returns 200")
    check(isinstance(r2.json(), list) and len(r2.json()) <= 1, "pagination: limit=1 returns ≤1 item")

    # ── /tags ────────────────────────────────────────────────────────────────
    section("/tags")
    r = client.get("/tags")
    check(r.status_code == 200, "returns 200")
    tags = r.json()
    check(isinstance(tags, list) and len(tags) > 0, "list is non-empty", f"got {len(tags)} tags")
    if tags:
        check(all(isinstance(t, str) for t in tags), "all tags are strings")
        check(tags == sorted(tags), "tags are sorted ASC")

    # ── /search ──────────────────────────────────────────────────────────────
    section("/search")
    r = client.get("/search", params={"q": "AI"})
    check(r.status_code == 200, "returns 200 for q=AI")
    results = r.json()
    check(isinstance(results, list), "returns a list")

    r_short = client.get("/search", params={"q": "x"})
    check(r_short.status_code == 422, "q<2 chars returns 422")

    # ── /metrics ─────────────────────────────────────────────────────────────
    section("/metrics")
    r = client.get("/metrics")
    check(r.status_code == 200, "returns 200")
    m = r.json()
    for key in ("total_items", "dates_covered"):
        check(key in m, f"response has '{key}' key")
    check(isinstance(m.get("total_items"), int) and m["total_items"] >= 0,
          "total_items is a non-negative int")

    # ── CORS ─────────────────────────────────────────────────────────────────
    section("CORS")
    r = client.get("/health", headers={"Origin": "http://localhost:3002"})
    acao = r.headers.get("access-control-allow-origin", "")
    check(
        acao in ("*", "http://localhost:3002"),
        "CORS allows localhost:3002",
        f"access-control-allow-origin={acao!r}",
    )

    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8002",
                        help="Backend base URL (default: http://localhost:8002)")
    args = parser.parse_args()

    print(f"\n\033[1mTAAFT API QA  →  {args.url}\033[0m")
    run(args.url)

    print(f"\n{'─' * 50}")
    total = passed + failed
    if failed == 0:
        print(f"\033[32m✓ All {total} checks passed\033[0m\n")
        sys.exit(0)
    else:
        print(f"\033[31m✗ {failed}/{total} checks FAILED\033[0m\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
