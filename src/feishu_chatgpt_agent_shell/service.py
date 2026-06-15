from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Set

from .artifacts import ArtifactStore
from .browser_runner import ChatGPTWebRunner
from .config import Settings
from .lark import LarkClient
from .memory import read_memory_for_prompt
from .planner import plan_request


class AgentService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = ArtifactStore(settings.data_dir)
        self.lark = LarkClient(settings)
        self.runner = ChatGPTWebRunner(settings)
        self.seen_message_ids: Set[str] = set()

    def handle_text_message(self, chat_id: str, message_id: str, text: str) -> Dict[str, Any]:
        if message_id and message_id in self.seen_message_ids:
            return {"status": "duplicate", "message_id": message_id}
        if message_id:
            self.seen_message_ids.add(message_id)

        memory_text = read_memory_for_prompt(self.settings.data_dir, chat_id, text)
        plan = plan_request(text, memory_text, self.settings)
        task = self.store.create_task(chat_id, text, {"plan": plan.prompt})
        try:
            images = self.runner.generate(plan.prompt_groups)
            for image in images:
                self.store.save_image(task, image.image_bytes, image.mime_type, image.metadata)
            zip_path = self.store.zip_task(task)
            image_keys = [self.lark.upload_image(Path(artifact.path)) for artifact in task.artifacts]
            message_id_out = self.lark.send_gallery_card(
                chat_id,
                title=f"Generated {len(image_keys)} image(s)",
                image_keys=image_keys,
                note=f"Task `{task.task_id}` completed. Zip saved locally: `{zip_path.name}`",
            )
            task.status = "completed"
            self.store.save_task(task)
            return {
                "status": "completed",
                "task_id": task.task_id,
                "image_count": len(task.artifacts),
                "feishu_message_id": message_id_out,
            }
        except Exception as exc:
            task.status = "failed"
            task.metadata["error"] = f"{exc.__class__.__name__}: {exc}"
            self.store.save_task(task)
            with_context = f"Task `{task.task_id}` failed: {exc.__class__.__name__}: {exc}"
            if self.settings.feishu_configured:
                self.lark.send_text(chat_id, with_context)
            return {"status": "failed", "task_id": task.task_id, "error": str(exc)}

    def health(self) -> Dict[str, Any]:
        return {
            "app": "ok",
            "feishu": {
                "configured": self.settings.feishu_configured,
                "domain": self.settings.feishu_domain,
            },
            "chatgpt_web": {
                "project_configured": bool(self.settings.chatgpt_project_url),
                "profile_dir": str(self.settings.chatgpt_browser_profile_dir),
                "run_mode": self.settings.chatgpt_run_mode,
                "restore_front_app": self.settings.chatgpt_restore_front_app,
                "authorized": self.settings.chatgpt_web_extraction_authorized,
            },
            "planner": {
                "configured": self.settings.planner_configured,
                "base_url": self.settings.planner_base_url,
                "model": self.settings.planner_model,
            },
            "vision": {
                "configured": self.settings.vision_configured,
                "base_url": self.settings.vision_base_url,
                "model": self.settings.vision_model,
            },
            "defaults": {
                "group_count": self.settings.default_group_count,
                "images_per_group": self.settings.default_images_per_group,
                "parallel_tabs": self.settings.parallel_tabs,
            },
        }
