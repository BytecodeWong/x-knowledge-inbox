from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .store import upsert_item


def _record_list(value: object) -> list[dict[str, object]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("items", "bookmarks", "data", "posts"):
            if key in value:
                return _record_list(value[key])
        return [value]
    raise ValueError("JSON must contain an object or a list of objects")


def load_records(path: str | Path) -> list[dict[str, object]]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if suffix in {".jsonl", ".ndjson"}:
        records = []
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.extend(_record_list(json.loads(line)))
        return records
    return _record_list(json.loads(file_path.read_text(encoding="utf-8")))


def normalize_record(record: dict[str, object]) -> dict[str, object]:
    def first(*keys: str) -> object:
        for key in keys:
            if record.get(key) not in (None, ""):
                return record[key]
        return ""

    return {
        "url": first("url", "link", "tweet_url", "permalink"),
        "title": first("title", "name"),
        "text": first("text", "content", "full_text", "description"),
        "author": first("author", "username", "user", "handle"),
        "source": first("source") or "x-bookmarks",
        "created_at": first("created_at", "date", "timestamp"),
        "tags": first("tags", "tag"),
        "notes": first("notes", "note"),
    }


def import_records(connection, records: Iterable[dict[str, object]]) -> tuple[int, int]:
    added = 0
    updated = 0
    for record in records:
        _, was_added = upsert_item(connection, normalize_record(record))
        if was_added:
            added += 1
        else:
            updated += 1
    return added, updated

