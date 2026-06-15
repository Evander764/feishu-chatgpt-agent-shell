from __future__ import annotations

import base64
import contextlib
import fcntl
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union
from urllib.parse import quote

import httpx

from .config import Settings
from .planner import PromptGroup


@dataclass
class DownloadedImage:
    image_bytes: bytes
    mime_type: str
    width: int
    height: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FrontmostAppSnapshot:
    app_name: str = ""
    chromium_window_id: Optional[int] = None


CHROMIUM_APP_NAMES = {
    "Arc",
    "Brave Browser",
    "Chromium",
    "Google Chrome",
    "Google Chrome Canary",
    "Microsoft Edge",
}


def wrap_image_prompt(prompt: str, image_count: int) -> str:
    count = max(1, min(5, int(image_count or 1)))
    noun = "one image" if count == 1 else f"{count} images"
    return (
        f"Please generate {noun} for this one prompt group. "
        "Keep one creative direction, but vary composition, lens, lighting, or details naturally. "
        "Do not create a collage or grid. Only generate images; avoid long explanations.\n\n"
        f"{prompt.strip()}"
    )


@contextlib.contextmanager
def profile_lock(profile_dir: Path) -> Iterator[None]:
    profile_dir.mkdir(parents=True, exist_ok=True)
    lock_file = profile_dir / "chatgpt-web.lock"
    with lock_file.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class ChatGPTWebRunner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, groups: List[PromptGroup]) -> List[DownloadedImage]:
        if not self.settings.chatgpt_web_extraction_authorized:
            raise RuntimeError(
                "CHATGPT_WEB_EXTRACTION_AUTHORIZED must be true before using web extraction."
            )
        if not self.settings.chatgpt_project_url:
            raise RuntimeError("CHATGPT_PROJECT_URL is required.")
        with profile_lock(self.settings.chatgpt_browser_profile_dir):
            original_app = self._launch()
            downloaded: List[DownloadedImage] = []
            for index, group in enumerate(groups[: self.settings.parallel_tabs]):
                prompt = wrap_image_prompt(group.prompt, group.image_count)
                downloaded.extend(self._run_one_group(index, group, prompt, original_app))
            return downloaded

    def open_for_login(self) -> None:
        original_app = self._frontmost_app_snapshot()
        profile = self.settings.chatgpt_browser_profile_dir
        profile.mkdir(parents=True, exist_ok=True)
        chrome = self._find_browser()
        url = self.settings.chatgpt_project_url or "https://chatgpt.com/"
        subprocess.Popen(
            [
                str(chrome),
                f"--user-data-dir={profile}",
                f"--remote-debugging-port={self.settings.chatgpt_cdp_port}",
                "--remote-debugging-address=127.0.0.1",
                "--remote-allow-origins=*",
                "--no-first-run",
                "--no-default-browser-check",
                "--new-window",
                url,
            ]
        )
        time.sleep(0.75)
        self._restore_frontmost_app(original_app)

    def _run_one_group(
        self,
        index: int,
        group: PromptGroup,
        prompt: str,
        original_app: FrontmostAppSnapshot,
    ) -> List[DownloadedImage]:
        target = self._new_target(self.settings.chatgpt_project_url)
        self._restore_frontmost_app(original_app)
        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError("Chrome target did not expose a WebSocket debugger URL.")
        cdp = _CDP(ws_url)
        try:
            cdp.call("Runtime.enable")
            cdp.call("Page.enable")
            self._restore_frontmost_app(original_app)
            expression = build_generation_expression(
                prompt=prompt,
                timeout_seconds=self.settings.chatgpt_wait_seconds,
            )
            cdp.call(
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "awaitPromise": True,
                    "returnByValue": True,
                    "timeout": (self.settings.chatgpt_wait_seconds + 45) * 1000,
                },
                timeout=self.settings.chatgpt_wait_seconds + 60,
            )
            payload = cdp.last_result_value or {}
            if payload.get("status") != "success":
                raise RuntimeError(payload.get("message") or "ChatGPT generation failed.")
            images = []
            for raw in payload.get("images", [])[: group.image_count]:
                header, b64 = raw["data_url"].split(",", 1)
                mime = header.split(";")[0].replace("data:", "") or "image/png"
                images.append(
                    DownloadedImage(
                        image_bytes=base64.b64decode(b64),
                        mime_type=mime,
                        width=int(raw.get("width") or 0),
                        height=int(raw.get("height") or 0),
                        metadata={
                            "source": "chatgpt-web",
                            "group_index": index,
                            "group_title": group.title,
                            "requested_images": group.image_count,
                            "dom_index": raw.get("dom_index"),
                            "alt": raw.get("alt"),
                        },
                    )
                )
            return images
        finally:
            cdp.close()
            if self.settings.chatgpt_close_after_job and target.get("id"):
                self._close_target(str(target["id"]))

    def _launch(self) -> FrontmostAppSnapshot:
        original_app = self._frontmost_app_snapshot()
        chrome = self._find_browser()
        profile = self.settings.chatgpt_browser_profile_dir
        profile.mkdir(parents=True, exist_ok=True)
        args = launch_args(
            chrome_path=chrome,
            profile_dir=profile,
            port=self.settings.chatgpt_cdp_port,
            url=self.settings.chatgpt_project_url,
            run_mode=self.settings.chatgpt_run_mode,
        )
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            wait_for_cdp(self.settings.chatgpt_cdp_port)
        finally:
            self._restore_frontmost_app(original_app)
        return original_app

    def _find_browser(self) -> Path:
        if self.settings.chatgpt_browser_executable:
            configured = Path(self.settings.chatgpt_browser_executable).expanduser()
            if configured.exists():
                return configured
        candidates = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
        for path in candidates:
            if path.exists():
                return path
        raise FileNotFoundError("No Chromium-compatible browser was found in /Applications.")

    def _new_target(self, url: str) -> Dict[str, Any]:
        encoded = quote(url, safe=":/?#[]@!$&'()*+,;=%")
        base = f"http://127.0.0.1:{self.settings.chatgpt_cdp_port}"
        resp = httpx.put(f"{base}/json/new?{encoded}", timeout=10)
        if resp.status_code >= 400:
            resp = httpx.get(f"{base}/json/new?{url}", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _close_target(self, target_id: str) -> None:
        base = f"http://127.0.0.1:{self.settings.chatgpt_cdp_port}"
        with contextlib.suppress(Exception):
            httpx.get(f"{base}/json/close/{quote(target_id, safe='')}", timeout=5)

    def _frontmost_app_snapshot(self) -> FrontmostAppSnapshot:
        if not self.settings.chatgpt_restore_front_app:
            return FrontmostAppSnapshot()
        app_name = self._frontmost_app_name()
        if not app_name:
            return FrontmostAppSnapshot()
        return FrontmostAppSnapshot(
            app_name=app_name,
            chromium_window_id=self._frontmost_chromium_window_id(app_name),
        )

    def _frontmost_app_name(self) -> str:
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to get name of first application process whose frontmost is true',
                ],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except Exception:
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""

    def _frontmost_chromium_window_id(self, app_name: str) -> Optional[int]:
        if app_name not in CHROMIUM_APP_NAMES:
            return None
        escaped = app_name.replace("\\", "\\\\").replace('"', '\\"')
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    (
                        f'tell application "{escaped}" to '
                        "if (count of windows) > 0 then get id of front window"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except Exception:
            return None
        if result.returncode != 0:
            return None
        try:
            return int(result.stdout.strip())
        except ValueError:
            return None

    def _restore_frontmost_app(
        self, snapshot: Union[FrontmostAppSnapshot, str]
    ) -> None:
        if not self.settings.chatgpt_restore_front_app:
            return
        if isinstance(snapshot, str):
            app_name = snapshot
            chromium_window_id = None
        else:
            app_name = snapshot.app_name
            chromium_window_id = snapshot.chromium_window_id
        if not app_name.strip():
            return
        escaped = app_name.replace("\\", "\\\\").replace('"', '\\"')
        if chromium_window_id is not None:
            script = (
                f'tell application "{escaped}"\n'
                "  activate\n"
                "  try\n"
                f"    set index of (first window whose id is {chromium_window_id}) to 1\n"
                "  end try\n"
                "end tell"
            )
        else:
            script = f'tell application "{escaped}" to activate'
        with contextlib.suppress(Exception):
            subprocess.run(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )


def launch_args(chrome_path: Path, profile_dir: Path, port: int, url: str, run_mode: str) -> List[str]:
    args = [
        str(chrome_path),
        f"--user-data-dir={profile_dir}",
        f"--remote-debugging-port={port}",
        "--remote-debugging-address=127.0.0.1",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-default-apps",
        "--new-window" if run_mode != "headless" else "",
        "--headless=new" if run_mode == "headless" else "",
        "--disable-gpu" if run_mode == "headless" else "",
        "--window-size=1600,1200" if run_mode == "headless" else "",
        "--start-minimized" if run_mode == "silent" else "",
        "--window-position=-32000,-32000" if run_mode == "silent" else "",
        "--window-size=1200,900" if run_mode == "silent" else "",
        url,
    ]
    return [arg for arg in args if arg]


def wait_for_cdp(port: int) -> None:
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        with contextlib.suppress(Exception):
            if httpx.get(f"{base}/json/version", timeout=1).status_code == 200:
                return
        time.sleep(0.25)
    raise RuntimeError("Chrome CDP did not become reachable.")


class _CDP:
    def __init__(self, ws_url: str):
        from websockets.sync.client import connect

        self.ws = connect(ws_url, open_timeout=8, max_size=64 * 1024 * 1024)
        self.seq = 0
        self.last_result_value: Optional[Dict[str, Any]] = None

    def call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
        self.seq += 1
        msg_id = self.seq
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = json.loads(self.ws.recv(timeout=max(1, int(deadline - time.time()))))
            if raw.get("id") != msg_id:
                continue
            if "error" in raw:
                raise RuntimeError(raw["error"])
            result = raw.get("result") or {}
            if method == "Runtime.evaluate":
                self.last_result_value = (
                    result.get("result", {}).get("value")
                    or result.get("result", {}).get("preview")
                    or {}
                )
            return result
        raise TimeoutError(f"CDP call timed out: {method}")

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self.ws.close()


def build_generation_expression(prompt: str, timeout_seconds: int) -> str:
    prompt_json = json.dumps(prompt)
    timeout_ms = int(timeout_seconds * 1000)
    return f"""
(async () => {{
  const prompt = {prompt_json};
  const timeoutMs = {timeout_ms};
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const largeImages = () => Array.from(document.images)
    .map((img, index) => {{
      const rect = img.getBoundingClientRect();
      return {{
        src: img.currentSrc || img.src || "",
        width: Math.round(rect.width || img.naturalWidth || 0),
        height: Math.round(rect.height || img.naturalHeight || 0),
        naturalWidth: img.naturalWidth || 0,
        naturalHeight: img.naturalHeight || 0,
        alt: img.alt || "",
        dom_index: index
      }};
    }})
    .filter((img) => img.src && img.width >= 240 && img.height >= 240 && img.naturalWidth >= 240);

  const baseline = new Set(largeImages().map((img) => img.src));
  const input = document.querySelector('textarea, [contenteditable="true"], div.ProseMirror');
  if (!input) return {{ status: "error", message: "No visible ChatGPT prompt input found." }};
  input.focus();
  if (input.tagName === "TEXTAREA") {{
    input.value = prompt;
    input.dispatchEvent(new Event("input", {{ bubbles: true }}));
  }} else {{
    input.textContent = prompt;
    input.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: "insertText", data: prompt }}));
  }}
  await sleep(300);
  const buttons = Array.from(document.querySelectorAll('button'));
  const send = buttons.find((b) => {{
    const label = `${{b.getAttribute("aria-label") || ""}} ${{b.textContent || ""}}`.toLowerCase();
    return !b.disabled && (label.includes("send") || label.includes("发送") || label.includes("submit"));
  }}) || buttons.reverse().find((b) => !b.disabled);
  if (!send) return {{ status: "error", message: "No send button found." }};
  send.click();

  const deadline = Date.now() + timeoutMs;
  let newest = [];
  while (Date.now() < deadline) {{
    const current = largeImages().filter((img) => !baseline.has(img.src));
    if (current.length > 0) {{
      newest = current;
      await sleep(2500);
      const still = largeImages().filter((img) => !baseline.has(img.src));
      if (still.length >= newest.length) {{
        newest = still;
        break;
      }}
    }}
    await sleep(1000);
  }}
  if (!newest.length) return {{ status: "error", message: "No new generated images found." }};

  const toDataUrl = async (src) => {{
    if (src.startsWith("data:")) return src;
    const response = await fetch(src);
    const blob = await response.blob();
    return await new Promise((resolve, reject) => {{
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    }});
  }};
  const images = [];
  for (const img of newest) {{
    try {{
      images.push({{ ...img, data_url: await toDataUrl(img.src) }});
    }} catch (error) {{}}
  }}
  return {{ status: "success", images }};
}})()
"""
