from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .config import Settings


class LarkClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._tenant_token: Optional[str] = None

    def tenant_token(self) -> str:
        if self._tenant_token:
            return self._tenant_token
        resp = httpx.post(
            f"{self.settings.feishu_domain}/open-apis/auth/v3/tenant_access_token/internal",
            json={
                "app_id": self.settings.feishu_app_id,
                "app_secret": self.settings.feishu_app_secret,
            },
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"Feishu tenant token failed: {payload}")
        self._tenant_token = payload["tenant_access_token"]
        return self._tenant_token

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.tenant_token()}"}

    def upload_image(self, image_path: Path) -> str:
        with image_path.open("rb") as handle:
            resp = httpx.post(
                f"{self.settings.feishu_domain}/open-apis/im/v1/images",
                headers=self._headers(),
                data={"image_type": "message"},
                files={"image": (image_path.name, handle, "application/octet-stream")},
                timeout=60,
            )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"Feishu image upload failed: {payload}")
        return payload["data"]["image_key"]

    def send_text(self, chat_id: str, text: str) -> str:
        return self.send_message(chat_id, "text", {"text": text})

    def send_gallery_card(self, chat_id: str, title: str, image_keys: List[str], note: str = "") -> str:
        card = build_gallery_card(title=title, image_keys=image_keys, note=note)
        return self.send_message(chat_id, "interactive", card)

    def send_message(self, chat_id: str, msg_type: str, content: Dict[str, Any]) -> str:
        resp = httpx.post(
            f"{self.settings.feishu_domain}/open-apis/im/v1/messages",
            params={"receive_id_type": "chat_id"},
            headers=self._headers(),
            json={
                "receive_id": chat_id,
                "msg_type": msg_type,
                "content": json.dumps(content, ensure_ascii=False),
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"Feishu send message failed: {payload}")
        return payload["data"]["message_id"]


def build_gallery_card(title: str, image_keys: List[str], note: str = "") -> Dict[str, Any]:
    elements: List[Dict[str, Any]] = []
    if note:
        elements.append({"tag": "markdown", "content": note})
    for index, key in enumerate(image_keys, start=1):
        elements.append(
            {
                "tag": "img",
                "img_key": key,
                "alt": {"tag": "plain_text", "content": f"image {index}"},
                "mode": "fit_horizontal",
            }
        )
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue",
        },
        "elements": elements,
    }


def parse_lark_event(body: Dict[str, Any], verification_token: str) -> Dict[str, Any]:
    if body.get("type") == "url_verification":
        if verification_token and body.get("token") != verification_token:
            raise ValueError("verification token mismatch")
        return {"challenge": body.get("challenge")}
    header = body.get("header") or {}
    if verification_token and header.get("token") and header.get("token") != verification_token:
        raise ValueError("verification token mismatch")
    event = body.get("event") or {}
    message = event.get("message") or {}
    return {
        "event_id": header.get("event_id") or message.get("message_id") or "",
        "message_id": message.get("message_id") or "",
        "chat_id": message.get("chat_id") or "",
        "chat_type": message.get("chat_type") or "",
        "message_type": message.get("message_type") or "",
        "text": extract_text_content(message.get("content") or ""),
    }


def extract_text_content(content: str) -> str:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return content
    return str(payload.get("text") or payload.get("content") or "").strip()

