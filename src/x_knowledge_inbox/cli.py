from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .importer import import_records, load_records
from .store import STATUSES, connect, get_item, items_since, list_items, render_csv, render_json, render_markdown, set_item_state, upsert_item


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="x-knowledge-inbox", description="A local-first inbox for turning X bookmarks into searchable knowledge.")
    sub = root.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a local SQLite database")
    init.add_argument("db", nargs="?", default="inbox.db")

    add = sub.add_parser("add", help="Add one saved post")
    add.add_argument("--db", default="inbox.db")
    add.add_argument("--url", required=True)
    add.add_argument("--title", default="")
    add.add_argument("--text", default="")
    add.add_argument("--author", default="")
    add.add_argument("--source", default="manual")
    add.add_argument("--created-at", default="")
    add.add_argument("--tags", default="")
    add.add_argument("--notes", default="")

    imp = sub.add_parser("import", help="Import JSON, JSONL, or CSV bookmarks")
    imp.add_argument("file")
    imp.add_argument("--db", default="inbox.db")

    ls = sub.add_parser("list", help="Search and list items")
    ls.add_argument("--db", default="inbox.db")
    ls.add_argument("--query", default="")
    ls.add_argument("--status", choices=STATUSES)
    ls.add_argument("--tag")
    ls.add_argument("--limit", type=int, default=50)

    show = sub.add_parser("show", help="Show one item as JSON")
    show.add_argument("id", type=int)
    show.add_argument("--db", default="inbox.db")

    review = sub.add_parser("review", help="Change status, tags, or notes")
    review.add_argument("id", type=int)
    review.add_argument("--db", default="inbox.db")
    review.add_argument("--status", choices=STATUSES)
    review.add_argument("--tags")
    review.add_argument("--note")

    digest = sub.add_parser("digest", help="Create a review digest")
    digest.add_argument("--db", default="inbox.db")
    digest.add_argument("--days", type=int, default=7)
    digest.add_argument("--limit", type=int, default=20)

    export = sub.add_parser("export", help="Export items")
    export.add_argument("--db", default="inbox.db")
    export.add_argument("--format", choices=("json", "markdown", "csv"), default="markdown")
    export.add_argument("--output", default="-")
    export.add_argument("--query", default="")
    export.add_argument("--status", choices=STATUSES)
    export.add_argument("--tag")
    export.add_argument("--limit", type=int, default=500)

    serve = sub.add_parser("serve", help="Open a local web inbox")
    serve.add_argument("--db", default="inbox.db")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return root


def print_items(items) -> None:
    if not items:
        print("No items found.")
        return
    for item in items:
        title = item.title or item.text.splitlines()[0][:80] or item.url
        print(f"[{item.id}] {item.status:<8} {title}")
        print(f"    {item.url}")
        if item.tags:
            print(f"    tags: {', '.join(item.tags)}")


def output_text(text: str, output: str) -> None:
    if output == "-":
        sys.stdout.write(text)
    else:
        Path(output).write_text(text, encoding="utf-8")
        print(f"Wrote {output}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "init":
        connection = connect(args.db)
        connection.close()
        print(f"Initialized {args.db}")
        return 0

    connection = connect(getattr(args, "db", "inbox.db"))
    try:
        if args.command == "add":
            item_id, added = upsert_item(connection, vars(args))
            print(f"{'Added' if added else 'Updated'} item {item_id}")
        elif args.command == "import":
            added, updated = import_records(connection, load_records(args.file))
            print(f"Imported {added} new item(s), updated {updated} existing item(s).")
        elif args.command == "list":
            print_items(list_items(connection, args.query, args.status, args.tag, args.limit))
        elif args.command == "show":
            item = get_item(connection, args.id)
            if item is None:
                print(f"Item not found: {args.id}", file=sys.stderr)
                return 1
            print(json.dumps(item.to_dict(), ensure_ascii=False, indent=2))
        elif args.command == "review":
            if args.status is None and args.tags is None and args.note is None:
                print("Provide at least one of --status, --tags, or --note.", file=sys.stderr)
                return 2
            item = set_item_state(connection, args.id, args.status, args.note, args.tags)
            print(f"Updated item {item.id}: {item.status}")
        elif args.command == "digest":
            print(render_markdown(items_since(connection, args.days, args.limit), f"X Inbox · last {args.days} days"))
        elif args.command == "export":
            items = list_items(connection, args.query, args.status, args.tag, args.limit)
            if args.format == "json":
                text = render_json(items)
            elif args.format == "csv":
                text = render_csv(items)
            else:
                text = render_markdown(items)
            output_text(text, args.output)
        elif args.command == "serve":
            from .web import serve
            serve(connection, args.host, args.port)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

