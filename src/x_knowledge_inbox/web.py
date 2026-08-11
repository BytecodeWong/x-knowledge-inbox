from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .store import connect, list_items, set_item_state


HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>X Knowledge Inbox</title>
  <style>
    :root { color-scheme: light; --ink:#19222d; --muted:#667482; --line:#dbe2e8; --accent:#0f766e; --soft:#f3f7f7; }
    * { box-sizing:border-box } body { margin:0; font:15px/1.55 system-ui,-apple-system,sans-serif; color:var(--ink); background:#fbfcfc; }
    header { position:sticky; top:0; z-index:2; background:rgba(251,252,252,.94); border-bottom:1px solid var(--line); padding:22px max(20px,calc((100% - 980px)/2)); backdrop-filter:blur(8px); }
    header h1 { margin:0 0 4px; font-size:24px; letter-spacing:-.03em; } header p { margin:0; color:var(--muted); }
    main { width:min(980px,calc(100% - 40px)); margin:24px auto 80px; }
    .toolbar { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:20px; } input,select { border:1px solid var(--line); border-radius:9px; padding:10px 12px; background:white; color:var(--ink); } input { flex:1; min-width:220px; }
    .item { background:white; border:1px solid var(--line); border-radius:14px; padding:17px 18px; margin:12px 0; box-shadow:0 2px 10px rgba(20,40,50,.03); } .item h2 { margin:0 0 5px; font-size:17px; } .item h2 a { color:inherit; text-decoration:none; } .meta { color:var(--muted); font-size:13px; } .text { white-space:pre-wrap; margin:12px 0; } .tags { color:var(--accent); font-size:13px; } .actions { display:flex; gap:8px; align-items:center; flex-wrap:wrap; } button { cursor:pointer; border:1px solid var(--line); border-radius:8px; background:white; padding:7px 10px; } button:hover { border-color:var(--accent); color:var(--accent); } .empty { padding:48px 0; text-align:center; color:var(--muted); }
  </style>
</head>
<body><header><h1>X Knowledge Inbox</h1><p>Review saved posts, turn them into actions, and keep your useful links searchable.</p></header>
<main><div class="toolbar"><input id="q" placeholder="Search titles, text, authors, notes…"><select id="status"><option value="">All statuses</option><option>inbox</option><option>reading</option><option>done</option><option>archived</option></select></div><section id="items"></section></main>
<script>
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function load(){ const p=new URLSearchParams({query:document.querySelector('#q').value,status:document.querySelector('#status').value}); const data=await fetch('/api/items?'+p); const items=await data.json(); const root=document.querySelector('#items'); if(!items.length){root.innerHTML='<div class="empty">No items found. Import your bookmarks from the CLI first.</div>';return;} root.innerHTML=items.map(i=>`<article class="item"><h2><a href="${esc(i.url)}" target="_blank" rel="noreferrer">${esc(i.title||i.url)}</a></h2><div class="meta">#${i.id} · ${esc(i.status)} · ${esc(i.author||'unknown author')}</div><div class="text">${esc(i.text||'No text imported.')}</div><div class="tags">${i.tags.map(t=>'#'+esc(t)).join(' ')}</div><div class="actions"><button onclick="setStatus(${i.id},'reading')">Reading</button><button onclick="setStatus(${i.id},'done')">Done</button><button onclick="setStatus(${i.id},'archived')">Archive</button></div></article>`).join(''); }
async function setStatus(id,status){ await fetch('/api/items/'+id+'/status',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({status})}); load(); }
document.querySelector('#q').addEventListener('input',load); document.querySelector('#status').addEventListener('change',load); load();
</script></body></html>'''


def make_handler(connection):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send(200, HTML.encode(), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/items":
                query = parse_qs(parsed.query)
                items = list_items(connection, query.get("query", [""])[0], query.get("status", [None])[0], limit=200)
                self._send(200, json.dumps([item.to_dict() for item in items], ensure_ascii=False).encode(), "application/json; charset=utf-8")
                return
            self._send(404, b"not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:  # noqa: N802
            parts = urlparse(self.path).path.strip("/").split("/")
            if len(parts) != 4 or parts[0] != "api" or parts[1] != "items" or parts[2] == "" or parts[3] != "status":
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            try:
                item_id = int(parts[2])
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                item = set_item_state(connection, item_id, status=payload.get("status"))
                self._send(200, json.dumps(item.to_dict(), ensure_ascii=False).encode(), "application/json; charset=utf-8")
            except (ValueError, json.JSONDecodeError) as exc:
                self._send(400, str(exc).encode(), "text/plain; charset=utf-8")

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def serve(connection, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(connection))
    print(f"X Knowledge Inbox running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
