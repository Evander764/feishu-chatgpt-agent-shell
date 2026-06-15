from __future__ import annotations

import json
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Artifact:
    artifact_id: str
    path: str
    mime_type: str
    bytes: int
    metadata: Dict[str, Any]


@dataclass
class TaskRecord:
    task_id: str
    chat_id: str
    text: str
    status: str
    created_at: float
    updated_at: float
    artifacts: List[Artifact]
    zip_path: str
    metadata: Dict[str, Any]


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root
        self.tasks_dir = root / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def create_task(self, chat_id: str, text: str, metadata: Dict[str, Any]) -> TaskRecord:
        task_id = f"task_{int(time.time() * 1000)}"
        task = TaskRecord(
            task_id=task_id,
            chat_id=chat_id,
            text=text,
            status="running",
            created_at=time.time(),
            updated_at=time.time(),
            artifacts=[],
            zip_path="",
            metadata=metadata,
        )
        self.save_task(task)
        return task

    def task_dir(self, task_id: str) -> Path:
        path = self.tasks_dir / task_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_image(
        self,
        task: TaskRecord,
        image_bytes: bytes,
        mime_type: str,
        metadata: Dict[str, Any],
    ) -> Artifact:
        ext = "png"
        if mime_type == "image/webp":
            ext = "webp"
        elif mime_type == "image/jpeg":
            ext = "jpg"
        artifact_id = f"img_{len(task.artifacts) + 1:03d}"
        path = self.task_dir(task.task_id) / f"{artifact_id}.{ext}"
        path.write_bytes(image_bytes)
        artifact = Artifact(
            artifact_id=artifact_id,
            path=str(path),
            mime_type=mime_type,
            bytes=len(image_bytes),
            metadata=metadata,
        )
        task.artifacts.append(artifact)
        task.updated_at = time.time()
        self.save_task(task)
        return artifact

    def zip_task(self, task: TaskRecord) -> Path:
        zip_path = self.task_dir(task.task_id) / f"{task.task_id}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for artifact in task.artifacts:
                zf.write(artifact.path, arcname=Path(artifact.path).name)
            manifest = json.dumps(self.task_payload(task), ensure_ascii=False, indent=2)
            zf.writestr("manifest.json", manifest)
        task.zip_path = str(zip_path)
        task.updated_at = time.time()
        self.save_task(task)
        return zip_path

    def save_task(self, task: TaskRecord) -> None:
        self.task_dir(task.task_id).joinpath("task.json").write_text(
            json.dumps(self.task_payload(task), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def task_payload(self, task: TaskRecord) -> Dict[str, Any]:
        payload = asdict(task)
        payload["artifacts"] = [asdict(artifact) for artifact in task.artifacts]
        return payload

