from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse


STORE_LIMIT = int(os.getenv("IMAP_WEBHOOK_TEST_STORE_LIMIT", "200"))
STORE_PATH = Path(
    os.getenv("IMAP_WEBHOOK_TEST_STORE_PATH", "/tmp/docuparse-imap-webhook-events.jsonl")
)

app = FastAPI(
    title="DocuParse IMAP Webhook Test API",
    description="Temporary receiver for backend-com IMAP reader webhook payloads.",
    version="0.1.0",
)

events: list[dict[str, Any]] = []


def _append_event(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    event = {
        "id": str(uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "headers": headers,
        "payload": payload,
    }
    events.append(event)
    del events[:-STORE_LIMIT]

    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORE_PATH.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "imap-webhook-test-api"}


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    latest = events[-1] if events else None
    pretty = json.dumps(latest, ensure_ascii=False, indent=2) if latest else "Nenhuma mensagem recebida ainda."
    return f"""
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <title>DocuParse IMAP Webhook Test API</title>
    <style>
      body {{ font-family: system-ui, sans-serif; margin: 32px; background: #f8fafc; color: #0f172a; }}
      code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
      pre {{ padding: 16px; background: #0f172a; color: #e2e8f0; overflow: auto; border-radius: 8px; }}
      .muted {{ color: #64748b; }}
    </style>
  </head>
  <body>
    <h1>DocuParse IMAP Webhook Test API</h1>
    <p class="muted">Configure <code>imap_reader_webhook_url</code> para <code>http://localhost:8015/imap-reader-webhook</code>.</p>
    <p>Mensagens em memoria: <strong>{len(events)}</strong></p>
    <p>JSONL: <code>{STORE_PATH}</code></p>
    <h2>Ultima mensagem</h2>
    <pre>{pretty}</pre>
  </body>
</html>
"""


@app.post("/imap-reader-webhook")
async def receive_imap_reader_webhook(request: Request) -> dict[str, Any]:
    payload = await request.json()
    event = _append_event(
        payload=payload,
        headers={
            "content-type": request.headers.get("content-type", ""),
            "user-agent": request.headers.get("user-agent", ""),
        },
    )
    attachments = payload.get("attachments") if isinstance(payload, dict) else None
    return {
        "status": "received",
        "id": event["id"],
        "received_at": event["received_at"],
        "attachments_count": len(attachments) if isinstance(attachments, list) else 0,
    }


@app.post("/echo_data")
async def echo_data_compat(request: Request) -> dict[str, Any]:
    payload = await request.json()
    event = _append_event(payload=payload, headers=dict(request.headers))
    return {"message": "Data received", "id": event["id"], "data": payload}


@app.get("/messages")
async def list_messages(limit: int = 20) -> dict[str, Any]:
    safe_limit = max(1, min(limit, STORE_LIMIT))
    return {
        "count": len(events),
        "messages": events[-safe_limit:],
    }


@app.get("/messages/latest")
async def latest_message() -> dict[str, Any]:
    if not events:
        return {"message": None}
    return {"message": events[-1]}


@app.delete("/messages")
async def clear_messages() -> dict[str, Any]:
    count = len(events)
    events.clear()
    return {"cleared": count}
