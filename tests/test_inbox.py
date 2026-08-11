import json
import tempfile
import unittest
from pathlib import Path

from x_knowledge_inbox.importer import import_records, load_records
from x_knowledge_inbox.store import connect, get_item, list_items, render_markdown, set_item_state, upsert_item


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.directory.name) / "inbox.db")

    def tearDown(self):
        self.db.close()
        self.directory.cleanup()

    def test_upsert_deduplicates_without_resetting_review_state(self):
        item_id, added = upsert_item(self.db, {"url": "https://x.com/a/1", "title": "First", "tags": ["AI"]})
        self.assertTrue(added)
        set_item_state(self.db, item_id, status="done", notes="Use this in the prototype")
        same_id, added_again = upsert_item(self.db, {"url": "https://x.com/a/1", "title": "Updated", "text": "New text"})

        self.assertEqual(item_id, same_id)
        self.assertFalse(added_again)
        item = get_item(self.db, item_id)
        self.assertEqual(item.status, "done")
        self.assertEqual(item.notes, "Use this in the prototype")
        self.assertEqual(item.title, "Updated")

    def test_import_json_and_search_by_text_or_tag(self):
        records = [
            {"url": "https://x.com/a/1", "title": "Agent notes", "text": "Useful workflow", "tags": ["AI", "tools"]},
            {"url": "https://x.com/a/2", "title": "Research", "text": "Bookmark workflow", "tags": "product"},
        ]
        added, updated = import_records(self.db, records)

        self.assertEqual((added, updated), (2, 0))
        self.assertEqual({item.title for item in list_items(self.db, query="workflow")}, {"Research", "Agent notes"})
        self.assertEqual([item.title for item in list_items(self.db, tag="ai")], ["Agent notes"])

    def test_markdown_export_contains_actionable_metadata(self):
        item_id, _ = upsert_item(self.db, {"url": "https://x.com/a/1", "title": "A saved idea", "text": "Make it useful.", "tags": "product"})
        set_item_state(self.db, item_id, status="reading", notes="Test this with five users")

        markdown = render_markdown(list_items(self.db))

        self.assertIn("# X Knowledge Inbox", markdown)
        self.assertIn("Status: reading", markdown)
        self.assertIn("Test this with five users", markdown)

    def test_load_records_supports_json_wrappers(self):
        path = Path(self.directory.name) / "bookmarks.json"
        path.write_text(json.dumps({"bookmarks": [{"link": "https://x.com/a/1", "content": "hello"}]}), encoding="utf-8")

        records = load_records(path)

        self.assertEqual(records[0]["link"], "https://x.com/a/1")


if __name__ == "__main__":
    unittest.main()
