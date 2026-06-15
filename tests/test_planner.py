from feishu_chatgpt_agent_shell.config import load_settings
from feishu_chatgpt_agent_shell.planner import fallback_plan, parse_plan_payload


def test_fallback_plan_keeps_groups_and_images_separate(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("DEFAULT_GROUP_COUNT=4\nDEFAULT_IMAGES_PER_GROUP=4\n", encoding="utf-8")
    settings = load_settings(str(env))

    plan = fallback_plan("生成极简咖啡杯图片", settings)

    assert len(plan.prompt_groups) == 4
    assert sum(group.image_count for group in plan.prompt_groups) == 16


def test_parse_plan_clamps_groups_and_image_count(tmp_path):
    settings = load_settings(str(tmp_path / "missing.env"))
    payload = {
        "intent": "generate_image",
        "prompt": "x",
        "prompt_groups": [
            {"title": "a", "prompt": "p1", "image_count": 9},
            {"title": "b", "prompt": "p2", "image_count": 2},
            {"title": "c", "prompt": "p3", "image_count": 2},
            {"title": "d", "prompt": "p4", "image_count": 2},
            {"title": "e", "prompt": "p5", "image_count": 2},
        ],
    }

    plan = parse_plan_payload(payload, settings, "fallback")

    assert len(plan.prompt_groups) == settings.parallel_tabs
    assert plan.prompt_groups[0].image_count == settings.max_images_per_group

