from pathlib import Path

from feishu_chatgpt_agent_shell.config import load_settings


def test_load_settings_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("CHATGPT_RUN_MODE", raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "CHATGPT_RUN_MODE=visible",
                "DEFAULT_GROUP_COUNT=9",
                "FEISHU_APP_ID=cli_test",
                "FEISHU_APP_SECRET=secret",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(str(env))

    assert settings.chatgpt_run_mode == "visible"
    assert settings.default_group_count == 4
    assert settings.feishu_configured
    assert isinstance(settings.data_dir, Path)

