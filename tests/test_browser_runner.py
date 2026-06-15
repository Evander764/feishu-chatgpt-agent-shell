from pathlib import Path

import pytest

from feishu_chatgpt_agent_shell.browser_runner import (
    FrontmostAppSnapshot,
    ChatGPTWebRunner,
    launch_args,
    wrap_image_prompt,
)
from feishu_chatgpt_agent_shell.config import load_settings


def test_wrap_image_prompt_uses_group_count_not_total():
    prompt = wrap_image_prompt("a ceramic cup", 4)

    assert "4 images" in prompt
    assert "collage" in prompt


def test_silent_launch_args_are_offscreen():
    args = launch_args(
        chrome_path=Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        profile_dir=Path("/tmp/profile"),
        port=9227,
        url="https://chatgpt.com/",
        run_mode="silent",
    )

    assert "--start-minimized" in args
    assert "--window-position=-32000,-32000" in args
    assert "--headless=new" not in args


def test_headless_launch_args_have_no_visible_window():
    args = launch_args(
        chrome_path=Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        profile_dir=Path("/tmp/profile"),
        port=9227,
        url="https://chatgpt.com/",
        run_mode="headless",
    )

    assert "--headless=new" in args
    assert "--new-window" not in args


def test_open_for_login_restores_previous_front_app(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        f"CHATGPT_BROWSER_PROFILE_DIR={tmp_path / 'profile'}\n"
        "CHATGPT_PROJECT_URL=https://chatgpt.com/g/example/project\n"
        "CHATGPT_RESTORE_FRONT_APP=true\n",
        encoding="utf-8",
    )
    settings = load_settings(str(env))
    runner = ChatGPTWebRunner(settings)
    popen_calls = []
    restore_calls = []

    monkeypatch.setattr(runner, "_find_browser", lambda: Path("/Applications/Fake Chrome"))
    monkeypatch.setattr(
        runner,
        "_frontmost_app_snapshot",
        lambda: FrontmostAppSnapshot(app_name="Codex"),
    )
    monkeypatch.setattr(runner, "_restore_frontmost_app", restore_calls.append)
    monkeypatch.setattr("feishu_chatgpt_agent_shell.browser_runner.time.sleep", lambda _: None)
    monkeypatch.setattr(
        "feishu_chatgpt_agent_shell.browser_runner.subprocess.Popen",
        lambda args: popen_calls.append(args),
    )

    runner.open_for_login()

    assert popen_calls
    assert "--new-window" in popen_calls[0]
    assert restore_calls == [FrontmostAppSnapshot(app_name="Codex")]


def test_web_extraction_requires_explicit_authorization(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "CHATGPT_PROJECT_URL=https://chatgpt.com/g/example/project\n"
        "CHATGPT_WEB_EXTRACTION_AUTHORIZED=false\n",
        encoding="utf-8",
    )
    settings = load_settings(str(env))

    with pytest.raises(RuntimeError, match="AUTHORIZED"):
        ChatGPTWebRunner(settings).generate([])
