from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from .config import load_settings
from .lark import parse_lark_event
from .service import AgentService

settings = load_settings()
service = AgentService(settings)
executor = ThreadPoolExecutor(max_workers=2)

app = FastAPI(title="Feishu ChatGPT Agent Shell", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, Any]:
    return service.health()


@app.post("/lark/events")
def lark_events(body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        event = parse_lark_event(body, settings.feishu_verification_token)
    except ValueError as exc:
        raise HTTPException(403, str(exc)) from exc
    if "challenge" in event:
        return {"challenge": event["challenge"]}
    if event.get("message_type") != "text" or not event.get("chat_id"):
        return {"status": "ignored"}
    executor.submit(
        service.handle_text_message,
        event["chat_id"],
        event.get("message_id") or event.get("event_id") or "",
        event.get("text") or "",
    )
    return {"status": "accepted"}


@app.post("/debug/run")
def debug_run(payload: Dict[str, str]) -> Dict[str, Any]:
    chat_id = payload.get("chat_id") or ""
    text = payload.get("text") or ""
    if not chat_id or not text:
        raise HTTPException(400, "chat_id and text are required")
    return service.handle_text_message(chat_id, f"debug_{hash(text)}", text)

