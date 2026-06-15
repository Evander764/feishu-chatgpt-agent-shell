from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


def load_dotenv(path: str = ".env") -> Dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}
    values: Dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def _get(name: str, default: str = "", dotenv: Optional[Dict[str, str]] = None) -> str:
    if name in os.environ:
        return os.environ[name]
    if dotenv and name in dotenv:
        return dotenv[name]
    return default


def _bool(value: str, default: bool = False) -> bool:
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(value: str, default: int, minimum: int = 0, maximum: int = 10_000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    public_base_url: str
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str
    feishu_domain: str
    chatgpt_project_url: str
    chatgpt_project_name: str
    chatgpt_browser_profile_dir: Path
    chatgpt_browser_executable: str
    chatgpt_cdp_port: int
    chatgpt_run_mode: str
    chatgpt_close_after_job: bool
    chatgpt_wait_seconds: int
    chatgpt_web_extraction_authorized: bool
    default_group_count: int
    default_images_per_group: int
    max_images_per_group: int
    parallel_tabs: int
    planner_base_url: str
    planner_api_key: str
    planner_model: str
    vision_base_url: str
    vision_api_key: str
    vision_model: str
    data_dir: Path

    @property
    def feishu_configured(self) -> bool:
        return bool(self.feishu_app_id and self.feishu_app_secret)

    @property
    def planner_configured(self) -> bool:
        return bool(self.planner_api_key and self.planner_model)

    @property
    def vision_configured(self) -> bool:
        return bool(self.vision_api_key and self.vision_model)


def load_settings(env_file: str = ".env") -> Settings:
    dotenv = load_dotenv(env_file)
    run_mode = _get("CHATGPT_RUN_MODE", "silent", dotenv).strip().lower()
    if run_mode not in {"visible", "silent", "headless"}:
        run_mode = "silent"
    return Settings(
        app_host=_get("APP_HOST", "127.0.0.1", dotenv),
        app_port=_int(_get("APP_PORT", "18080", dotenv), 18080, 1, 65535),
        public_base_url=_get("PUBLIC_BASE_URL", "", dotenv).rstrip("/"),
        feishu_app_id=_get("FEISHU_APP_ID", "", dotenv),
        feishu_app_secret=_get("FEISHU_APP_SECRET", "", dotenv),
        feishu_verification_token=_get("FEISHU_VERIFICATION_TOKEN", "", dotenv),
        feishu_domain=_get("FEISHU_DOMAIN", "https://open.feishu.cn", dotenv).rstrip("/"),
        chatgpt_project_url=_get("CHATGPT_PROJECT_URL", "", dotenv),
        chatgpt_project_name=_get("CHATGPT_PROJECT_NAME", "", dotenv),
        chatgpt_browser_profile_dir=Path(
            _get(
                "CHATGPT_BROWSER_PROFILE_DIR",
                "~/Library/Application Support/Feishu ChatGPT Agent Shell/browser-profile",
                dotenv,
            )
        ).expanduser(),
        chatgpt_browser_executable=_get("CHATGPT_BROWSER_EXECUTABLE", "", dotenv),
        chatgpt_cdp_port=_int(_get("CHATGPT_CDP_PORT", "9227", dotenv), 9227, 1, 65535),
        chatgpt_run_mode=run_mode,
        chatgpt_close_after_job=_bool(_get("CHATGPT_CLOSE_AFTER_JOB", "true", dotenv), True),
        chatgpt_wait_seconds=_int(_get("CHATGPT_WAIT_SECONDS", "240", dotenv), 240, 30, 1800),
        chatgpt_web_extraction_authorized=_bool(
            _get("CHATGPT_WEB_EXTRACTION_AUTHORIZED", "false", dotenv), False
        ),
        default_group_count=_int(_get("DEFAULT_GROUP_COUNT", "4", dotenv), 4, 1, 4),
        default_images_per_group=_int(_get("DEFAULT_IMAGES_PER_GROUP", "4", dotenv), 4, 1, 5),
        max_images_per_group=_int(_get("MAX_IMAGES_PER_GROUP", "5", dotenv), 5, 1, 5),
        parallel_tabs=_int(_get("PARALLEL_TABS", "4", dotenv), 4, 1, 4),
        planner_base_url=_get("PLANNER_BASE_URL", "https://api.openai.com/v1", dotenv).rstrip("/"),
        planner_api_key=_get("PLANNER_API_KEY", "", dotenv),
        planner_model=_get("PLANNER_MODEL", "gpt-4.1-mini", dotenv),
        vision_base_url=_get("VISION_BASE_URL", "https://api.openai.com/v1", dotenv).rstrip("/"),
        vision_api_key=_get("VISION_API_KEY", "", dotenv),
        vision_model=_get("VISION_MODEL", "gpt-4.1-mini", dotenv),
        data_dir=Path(_get("DATA_DIR", "./data", dotenv)).expanduser(),
    )

