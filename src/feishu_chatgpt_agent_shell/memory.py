from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_TOPICS = [
    "composition",
    "lighting",
    "color",
    "texture",
    "subject",
    "emotion",
    "platform_xhs",
    "negative",
]


@dataclass
class MemoryEvent:
    event_id: str
    created_at: float
    chat_id: str
    kind: str
    raw_feedback: str
    selected_index: int
    task_id: str
    summary: str
    positive_rules: List[str]
    negative_rules: List[str]


def memory_path(data_dir: Path, chat_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in chat_id)
    return data_dir / "memory" / f"{safe}.json"


def load_memory(data_dir: Path, chat_id: str) -> Dict[str, Any]:
    path = memory_path(data_dir, chat_id)
    if not path.exists():
        return {
            "schema_version": 1,
            "events": [],
            "topics": {topic: {"active_rules": []} for topic in DEFAULT_TOPICS},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_memory(data_dir: Path, chat_id: str, payload: Dict[str, Any]) -> None:
    path = memory_path(data_dir, chat_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_memory_for_prompt(data_dir: Path, chat_id: str, query_text: str, limit: int = 12) -> str:
    payload = load_memory(data_dir, chat_id)
    query = query_text.lower()
    rules: List[str] = []
    for topic, topic_payload in payload.get("topics", {}).items():
        active = topic_payload.get("active_rules", [])
        if not active:
            continue
        if topic in query or topic in {"composition", "lighting", "color", "texture", "negative"}:
            rules.extend(str(item) for item in active)
    return "\n".join(f"- {rule}" for rule in rules[:limit])


def record_selection_feedback(
    data_dir: Path,
    chat_id: str,
    task_id: str,
    selected_index: int,
    raw_feedback: str,
    summary: str,
    positive_rules: List[str],
    negative_rules: List[str],
) -> MemoryEvent:
    payload = load_memory(data_dir, chat_id)
    event = MemoryEvent(
        event_id=f"mem_{int(time.time() * 1000)}",
        created_at=time.time(),
        chat_id=chat_id,
        kind="selection_feedback",
        raw_feedback=raw_feedback,
        selected_index=selected_index,
        task_id=task_id,
        summary=summary,
        positive_rules=positive_rules,
        negative_rules=negative_rules,
    )
    payload.setdefault("events", []).append(asdict(event))
    topics = payload.setdefault("topics", {})
    topics.setdefault("composition", {"active_rules": []})["active_rules"].extend(positive_rules)
    topics.setdefault("negative", {"active_rules": []})["active_rules"].extend(negative_rules)
    save_memory(data_dir, chat_id, payload)
    return event

