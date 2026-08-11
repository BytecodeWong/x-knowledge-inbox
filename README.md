# X Knowledge Inbox

Turn saved X posts into a small, searchable, actionable knowledge base.

Most people save useful posts faster than they can revisit them. `x-knowledge-inbox` gives those saved posts an inbox workflow: import, search, tag, review, digest, and export.

The MVP is local-first and does not scrape X or automate posts, likes, follows, replies, or messages. It works with user-selected URLs and user-owned JSON/JSONL/CSV exports.

## Quick start

Requires Python 3.10+ and has no runtime dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

x-knowledge-inbox init inbox.db
x-knowledge-inbox import examples/sample-bookmarks.json --db inbox.db
x-knowledge-inbox list --db inbox.db
x-knowledge-inbox list --db inbox.db --query agent
x-knowledge-inbox review 1 --db inbox.db --status reading --tags agents,security
x-knowledge-inbox digest --db inbox.db --days 30
x-knowledge-inbox export --db inbox.db --format markdown --output bookmarks.md
```

Open the local web inbox:

```bash
x-knowledge-inbox serve --db inbox.db
# open http://127.0.0.1:8765
```

## Import format

JSON can be a list, a single object, or an object containing `items`/`bookmarks`:

```json
[
  {
    "url": "https://x.com/example/status/123",
    "title": "A useful thread",
    "text": "The imported post text goes here.",
    "author": "@example",
    "created_at": "2026-08-11T08:00:00Z",
    "tags": ["ai", "tools"]
  }
]
```

CSV uses the same field names. Aliases such as `link`, `tweet_url`, `content`, `full_text`, `username`, and `date` are accepted. Importing the same URL again updates available metadata without resetting its review state or notes.

## Workflow

`inbox` → `reading` → `done` or `archived`

The CLI is useful for automation and backups. The local web view is intentionally small: search the inbox and move items through review states without sending data to a hosted service.

## Product thesis

The first customer is a heavy X user who saves posts about AI, software, markets, research, or tools and repeatedly says “I know I saved that somewhere.” The MVP measures value through:

- time to find a saved post;
- percentage of saved items reviewed;
- number of items converted into notes or actions;
- weekly active inbox users.

The next validation step is to give the tool to 10 people with 500+ saved posts and measure whether they return to process a weekly digest.

## Roadmap

- Import adapters for more user-owned export formats.
- Better local full-text search and saved views.
- Optional local embeddings for semantic search.
- Official X API connector only after reviewing current platform rules and privacy requirements.
- Optional integrations for Obsidian, Notion, and read-later workflows.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m x_knowledge_inbox.cli --help
```

See [SECURITY.md](SECURITY.md) for data-handling boundaries and [CONTRIBUTING.md](CONTRIBUTING.md) for development rules.

