from __future__ import annotations

import asyncio
import contextlib
import json
import os
from collections import deque
from datetime import datetime, timezone
from itertools import count
from typing import Any

import nats
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

BASE_DIR = os.path.dirname(__file__)
INDEX_FILE = os.path.join(BASE_DIR, "index.html")
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
MAX_EVENTS = 300

app = FastAPI(title="TrackYourIron Site")

_events: deque[dict[str, Any]] = deque(maxlen=MAX_EVENTS)
_events_lock = asyncio.Lock()
_counter = count(1)


def _next_event_id() -> int:
    return next(_counter)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _append_event(subject: str, payload: dict[str, Any], raw: str | None = None) -> None:
    item = {
        "id": _next_event_id(),
        "subject": subject,
        "timestamp": _now_iso(),
        "payload": payload,
        "raw": raw,
    }
    async with _events_lock:
        _events.appendleft(item)


async def _listen_subject(sub: nats.aio.subscription.Subscription) -> None:
    async for msg in sub.messages:
        data = msg.data.decode(errors="replace")
        try:
            payload = json.loads(data)
            if not isinstance(payload, dict):
                payload = {"value": payload}
            await _append_event(msg.subject, payload)
        except json.JSONDecodeError:
            await _append_event(msg.subject, {"decode_error": True}, raw=data)


async def _nats_listener() -> None:
    while True:
        try:
            nc = await nats.connect(NATS_URL)
            subs = [
                await nc.subscribe("events.price_dropped"),
                await nc.subscribe("events.telegram_update"),
            ]
            await asyncio.gather(*[_listen_subject(s) for s in subs])
        except Exception:
            await asyncio.sleep(2)


@app.on_event("startup")
async def startup_event() -> None:
    app.state.nats_task = asyncio.create_task(_nats_listener())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    task = getattr(app.state, "nats_task", None)
    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/events")
async def events(limit: int = 100) -> JSONResponse:
    safe_limit = max(1, min(limit, MAX_EVENTS))
    async with _events_lock:
        data = list(_events)[:safe_limit]
    return JSONResponse(data)
