from pathlib import Path

import pytest

from feishu_chatgpt_agent_shell.browser_runner import (
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

