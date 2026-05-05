#!/usr/bin/env python3
"""
Purge old SQL files from the processed/ directory.
Usage: python scripts/purge_processed.py [--days 90] [--dry-run] [--dir ./processed]
Default: delete .sql and .failed files older than 90 days.
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90,
                        help="Delete files older than N days (default: 90)")
    parser.add_argument("--dir", default="processed",
                        help="Directory to purge (default: ./processed)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List files that would be deleted without deleting them")
    args = parser.parse_args()

    processed_dir = Path(args.dir)
    if not processed_dir.is_dir():
        print(f"Directory not found: {processed_dir}")
        sys.exit(0)

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=args.days)
    candidates = sorted(
        f for f in processed_dir.iterdir()
        if f.suffix in (".sql", ".failed") and f.is_file()
    )

    to_delete = [
        f for f in candidates
        if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) < cutoff
    ]

    if not to_delete:
        print(f"Nothing to purge (0 files older than {args.days} days).")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Purging {len(to_delete)} file(s) "
          f"older than {args.days} days from {processed_dir}/")

    for f in to_delete:
        age_days = (datetime.now(tz=timezone.utc) -
                    datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)).days
        if args.dry_run:
            print(f"  would delete  {f.name}  ({age_days}d old)")
        else:
            f.unlink()
            print(f"  deleted  {f.name}  ({age_days}d old)")

    if not args.dry_run:
        print(f"Done — {len(to_delete)} file(s) removed.")


if __name__ == "__main__":
    main()
