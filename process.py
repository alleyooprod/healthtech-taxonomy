#!/usr/bin/env python3
"""CLI entry point for healthtech taxonomy processing."""
import argparse
import sys
import uuid

from config import DEFAULT_WORKERS, DEFAULT_MODEL
from core.pipeline import Pipeline
from core.triage import triage_urls
from core.url_resolver import extract_urls_from_text, parse_file
from storage.db import Database
from storage.export import export_csv, export_json, export_markdown


def main():
    parser = argparse.ArgumentParser(
        description="Healthtech Taxonomy Builder - Automated company research and classification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python process.py urls.txt                    # Process URLs from a file
  python process.py --url https://www.oura.com  # Process a single URL
  python process.py urls.csv --workers 3        # Slower but cheaper
  python process.py --retry-failed              # Retry all failed jobs
  python process.py --reclassify                # Re-classify with updated taxonomy
  python process.py --export json               # Export current data
  python process.py urls.txt --dry-run          # Validate URLs without processing
        """,
    )
    parser.add_argument("input_file", nargs="?", help="File containing URLs (.txt, .csv, .xlsx, .md)")
    parser.add_argument("--url", help="Single URL to process")
    parser.add_argument("--resume", metavar="BATCH_ID", help="Resume an incomplete batch")
    parser.add_argument("--retry-failed", action="store_true", help="Retry all failed jobs")
    parser.add_argument("--reclassify", action="store_true", help="Re-classify all companies")
    parser.add_argument("--force", action="store_true", help="Re-process even if URL already exists")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"Concurrent workers (default: {DEFAULT_WORKERS})")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=["claude-opus-4-6", "sonnet", "opus", "haiku"], help=f"Claude model (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="Validate URLs only, no research")
    parser.add_argument("--triage", action="store_true", help="Run pre-validation triage only (scrape + relevance check)")
    parser.add_argument("--export", choices=["json", "md", "csv"], help="Export current data and exit")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")

    args = parser.parse_args()
    db = Database()

    # Export mode
    if args.export:
        if args.export == "json":
            path = export_json(db)
        elif args.export == "md":
            path = export_markdown(db)
        elif args.export == "csv":
            path = export_csv(db)
        print(f"Exported to: {path}")
        return

    # Stats mode
    if args.stats:
        stats = db.get_stats()
        cat_stats = db.get_category_stats()
        print(f"\nTotal companies: {stats['total_companies']}")
        print(f"Total categories: {stats['total_categories']}")
        print(f"Last updated: {stats['last_updated'] or 'Never'}\n")
        print("Categories:")
        for cat in cat_stats:
            if cat["company_count"] > 0 or cat["parent_id"] is None:
                prefix = "  " if cat["parent_id"] else ""
                print(f"  {prefix}{cat['name']}: {cat['company_count']}")
        batches = db.get_recent_batches(5)
        if batches:
            print("\nRecent batches:")
            for b in batches:
                print(f"  {b['batch_id']}: {b['done']}/{b['total']} done, {b['errors']} errors ({b['started']})")
        return

    # Triage mode
    if args.triage:
        urls = []
        if args.url:
            urls = [args.url]
        elif args.input_file:
            urls = parse_file(args.input_file)
        else:
            print("Provide --url or input_file with --triage")
            return

        if not urls:
            print("No URLs found in input.")
            return

        print(f"\nTriaging {len(urls)} URLs...\n")
        results = triage_urls(urls)
        for r in results:
            icon = {"valid": "[OK]", "suspect": "[??]", "error": "[!!]"}.get(r.status, "[--]")
            print(f"  {icon} {r.original_url}")
            if r.resolved_url != r.original_url:
                print(f"       -> {r.resolved_url}")
            if r.title:
                print(f"       Title: {r.title}")
            print(f"       {r.reason}")
            print()

        valid = sum(1 for r in results if r.status == "valid")
        suspect = sum(1 for r in results if r.status == "suspect")
        errors = sum(1 for r in results if r.status == "error")
        print(f"Summary: {valid} valid, {suspect} suspect, {errors} errors")
        return

    pipeline = Pipeline(db, workers=args.workers, model=args.model)

    # Resume mode
    if args.resume:
        pipeline.resume(args.resume)
        return

    # Retry failed
    if args.retry_failed:
        pipeline.retry_failed()
        return

    # Reclassify
    if args.reclassify:
        pipeline.reclassify_all()
        return

    # Collect URLs
    urls = []
    if args.url:
        urls = [args.url]
    elif args.input_file == "-":
        text = sys.stdin.read()
        urls = extract_urls_from_text(text)
    elif args.input_file:
        urls = parse_file(args.input_file)
    else:
        parser.print_help()
        return

    if not urls:
        print("No URLs found in input.")
        return

    # Generate batch ID and run
    batch_id = str(uuid.uuid4())[:8]
    pipeline.run(urls, batch_id, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
