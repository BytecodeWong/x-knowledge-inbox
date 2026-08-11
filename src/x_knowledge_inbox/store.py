from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import csv
import io
import json
from pathlib import Path
import sqlite3
from typing import Iterable, Sequence


STATUSES = ("inbox", "reading", "done", "archived")


@dataclass(frozen=True)
class Item:
    id: int
    url: str
    title: str
    text: str
    author: str
    source: str
    created_at: str
    added_at: str
    status: str
    tags: tuple[str, ...]
    notes: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["tags"] = list(self.tags)
        return result


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_tags(tags: str | Sequence[str] | None) -> tuple[str, ...]:
    if tags is None:
        return ()
    values = tags.split(",") if isinstance(tags, str) else tags
    normalized = []
    for value in values:
        tag = str(value).strip().lower().lstrip("#")
        if tag and tag not in normalized:
            normalized.append(tag[:40])
    return tuple(sorted(normalized))


def _tags_text(tags: str | Sequence[str] | None) -> str:
    values = normalize_tags(tags)
    return "|" + "|".join(values) + "|" if values else "||"


def _tags_from_text(value: str | None) -> tuple[str, ...]:
    if not value or value == "||":
        return ()
    return tuple(part for part in value.strip("|").split("|") if part)


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL DEFAULT '',
            text TEXT NOT NULL DEFAULT '',
            author TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'import',
            created_at TEXT NOT NULL DEFAULT '',
            added_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'inbox',
            tags TEXT NOT NULL DEFAULT '||',
            notes TEXT NOT NULL DEFAULT '',
            CHECK (status IN ('inbox', 'reading', 'done', 'archived'))
        )
        """
    )
    connection.commit()
    return connection


def _row_to_item(row: sqlite3.Row) -> Item:
    return Item(
        id=row["id"], url=row["url"], title=row["title"], text=row["text"],
        author=row["author"], source=row["source"], created_at=row["created_at"],
        added_at=row["added_at"], status=row["status"], tags=_tags_from_text(row["tags"]),
        notes=row["notes"],
    )


def upsert_item(connection: sqlite3.Connection, data: dict[str, object]) -> tuple[int, bool]:
    url = str(data.get("url") or "").strip()
    if not url:
        raise ValueError("each item needs a non-empty url")
    existing = connection.execute("SELECT id FROM items WHERE url = ?", (url,)).fetchone()
    fields = {
        "title": str(data.get("title") or "").strip(),
        "text": str(data.get("text") or "").strip(),
        "author": str(data.get("author") or "").strip(),
        "source": str(data.get("source") or "import").strip() or "import",
        "created_at": str(data.get("created_at") or "").strip(),
        "tags": _tags_text(data.get("tags")),
        "notes": str(data.get("notes") or "").strip(),
    }
    if existing:
        connection.execute(
            """UPDATE items SET title = CASE WHEN ? <> '' THEN ? ELSE title END,
               text = CASE WHEN ? <> '' THEN ? ELSE text END,
               author = CASE WHEN ? <> '' THEN ? ELSE author END,
               source = CASE WHEN ? <> '' THEN ? ELSE source END,
               created_at = CASE WHEN ? <> '' THEN ? ELSE created_at END,
               tags = CASE WHEN ? <> '||' THEN ? ELSE tags END,
               notes = CASE WHEN ? <> '' THEN ? ELSE notes END
               WHERE id = ?""",
            (fields["title"], fields["title"], fields["text"], fields["text"],
             fields["author"], fields["author"], fields["source"], fields["source"],
             fields["created_at"], fields["created_at"], fields["tags"], fields["tags"],
             fields["notes"], fields["notes"], existing["id"]),
        )
        connection.commit()
        return int(existing["id"]), False
    cursor = connection.execute(
        """INSERT INTO items (url, title, text, author, source, created_at, added_at, tags, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (url, fields["title"], fields["text"], fields["author"], fields["source"],
         fields["created_at"], now_iso(), fields["tags"], fields["notes"]),
    )
    connection.commit()
    return int(cursor.lastrowid), True


def get_item(connection: sqlite3.Connection, item_id: int) -> Item | None:
    row = connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return _row_to_item(row) if row else None


def list_items(
    connection: sqlite3.Connection,
    query: str = "",
    status: str | None = None,
    tag: str | None = None,
    limit: int = 50,
) -> list[Item]:
    clauses = []
    params: list[object] = []
    if query.strip():
        escaped = query.strip().replace("!", "!!").replace("%", "!%").replace("_", "!_")
        like = f"%{escaped}%"
        clauses.append("(url LIKE ? ESCAPE '!' OR title LIKE ? ESCAPE '!' OR text LIKE ? ESCAPE '!' OR author LIKE ? ESCAPE '!' OR notes LIKE ? ESCAPE '!')")
        params.extend([like] * 5)
    if status:
        if status not in STATUSES:
            raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
        clauses.append("status = ?")
        params.append(status)
    if tag:
        clauses.append("tags LIKE ? ESCAPE '!'")
        params.append("%|" + tag.strip().lower().replace("!", "!!").replace("%", "!%").replace("_", "!_") + "|%")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = connection.execute(
        f"SELECT * FROM items{where} ORDER BY CASE status WHEN 'inbox' THEN 0 WHEN 'reading' THEN 1 WHEN 'done' THEN 2 ELSE 3 END, COALESCE(NULLIF(created_at, ''), added_at) DESC, id DESC LIMIT ?",
        (*params, max(1, min(limit, 500))),
    ).fetchall()
    return [_row_to_item(row) for row in rows]


def set_item_state(
    connection: sqlite3.Connection,
    item_id: int,
    status: str | None = None,
    notes: str | None = None,
    tags: str | Sequence[str] | None = None,
) -> Item:
    if get_item(connection, item_id) is None:
        raise ValueError(f"item not found: {item_id}")
    updates: list[str] = []
    params: list[object] = []
    if status is not None:
        if status not in STATUSES:
            raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
        updates.append("status = ?")
        params.append(status)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes.strip())
    if tags is not None:
        updates.append("tags = ?")
        params.append(_tags_text(tags))
    if updates:
        connection.execute(f"UPDATE items SET {', '.join(updates)} WHERE id = ?", (*params, item_id))
        connection.commit()
    return get_item(connection, item_id)  # type: ignore[return-value]


def items_since(connection: sqlite3.Connection, days: int, limit: int = 20) -> list[Item]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, days))).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = connection.execute(
        "SELECT * FROM items WHERE added_at >= ? AND status <> 'archived' ORDER BY added_at DESC LIMIT ?",
        (cutoff, max(1, min(limit, 500))),
    ).fetchall()
    return [_row_to_item(row) for row in rows]


def render_markdown(items: Iterable[Item], heading: str = "X Knowledge Inbox") -> str:
    lines = [f"# {heading}", ""]
    for item in items:
        title = item.title or item.text.splitlines()[0][:80] or item.url
        lines.extend([f"## {title}", f"- URL: {item.url}", f"- Status: {item.status}"])
        if item.author:
            lines.append(f"- Author: {item.author}")
        if item.tags:
            lines.append(f"- Tags: {', '.join(item.tags)}")
        if item.notes:
            lines.append(f"- Notes: {item.notes}")
        lines.extend(["", item.text.strip() or "_(No text imported.)_", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_csv(items: Iterable[Item]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "url", "title", "text", "author", "source", "created_at", "added_at", "status", "tags", "notes"])
    writer.writeheader()
    for item in items:
        row = item.to_dict()
        row["tags"] = ",".join(item.tags)
        writer.writerow(row)
    return output.getvalue()


def render_json(items: Iterable[Item]) -> str:
    return json.dumps([item.to_dict() for item in items], ensure_ascii=False, indent=2) + "\n"
