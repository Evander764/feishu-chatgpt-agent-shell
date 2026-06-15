from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from .config import Settings


@dataclass
class PromptGroup:
    title: str
    prompt: str
    image_count: int


@dataclass
class Plan:
    intent: str
    prompt: str
    reply: str
    prompt_groups: List[PromptGroup]


def clamp_group_count(value: int) -> int:
    return max(1, min(4, int(value or 1)))


def clamp_images_per_group(value: int, max_images: int = 5) -> int:
    return max(1, min(max_images, int(value or 1)))


def fallback_plan(user_text: str, settings: Settings) -> Plan:
    group_count = clamp_group_count(settings.default_group_count)
    per_group = clamp_images_per_group(
        settings.default_images_per_group, settings.max_images_per_group
    )
    directions = [
        ("main visual", "Strong cover composition, clear subject, premium social feed visual."),
        ("story scene", "Environmental storytelling, clean frame, natural context."),
        ("texture detail", "Material texture, refined lighting, close visual quality."),
        ("xhs share", "Xiaohongshu-friendly layout, memorable details, polished mood."),
    ]
    groups = [
        PromptGroup(
            title=directions[index % len(directions)][0],
            prompt=f"{user_text}\n\nCreative direction: {directions[index % len(directions)][1]}",
            image_count=per_group,
        )
        for index in range(group_count)
    ]
    return Plan(intent="generate_image", prompt=user_text, reply="", prompt_groups=groups)


def parse_plan_payload(payload: Dict[str, Any], settings: Settings, fallback_text: str) -> Plan:
    intent = str(payload.get("intent") or "generate_image")
    prompt = str(payload.get("prompt") or fallback_text)
    reply = str(payload.get("reply") or "")
    groups_payload = payload.get("prompt_groups") or []
    groups: List[PromptGroup] = []
    if isinstance(groups_payload, list):
        for index, raw in enumerate(groups_payload[: settings.parallel_tabs]):
            if not isinstance(raw, dict):
                continue
            group_prompt = str(raw.get("prompt") or "").strip()
            if not group_prompt:
                continue
            groups.append(
                PromptGroup(
                    title=str(raw.get("title") or f"group {index + 1}"),
                    prompt=group_prompt,
                    image_count=clamp_images_per_group(
                        int(raw.get("image_count") or settings.default_images_per_group),
                        settings.max_images_per_group,
                    ),
                )
            )
    if not groups:
        return fallback_plan(fallback_text, settings)
    return Plan(intent=intent, prompt=prompt, reply=reply, prompt_groups=groups)


def plan_request(user_text: str, memory_text: str, settings: Settings) -> Plan:
    if not settings.planner_configured:
        return fallback_plan(user_text, settings)

    import httpx

    system = (
        "You are an image prompt planner for a Feishu bot. Return strict JSON only. "
        "Separate prompt_groups from images per group. Four groups with four images each "
        "means sixteen images. Use aesthetic memory only when relevant."
    )
    schema_hint = {
        "intent": "generate_image",
        "prompt": "short request summary",
        "reply": "",
        "prompt_groups": [
            {"title": "main visual", "prompt": "one group prompt", "image_count": 4}
        ],
    }
    body = {
        "model": settings.planner_model,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"User request:\n{user_text}\n\nRelevant aesthetic memory:\n{memory_text}\n\n"
                    f"JSON schema example:\n{json.dumps(schema_hint, ensure_ascii=False)}"
                ),
            },
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.planner_api_key}"}
    try:
        resp = httpx.post(
            f"{settings.planner_base_url}/chat/completions",
            headers=headers,
            json=body,
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        payload = json.loads(content)
        return parse_plan_payload(payload, settings, user_text)
    except Exception:
        return fallback_plan(user_text, settings)


def plan_to_dict(plan: Plan) -> Dict[str, Any]:
    return asdict(plan)
