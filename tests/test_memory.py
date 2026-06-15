from feishu_chatgpt_agent_shell.memory import (
    load_memory,
    read_memory_for_prompt,
    record_selection_feedback,
)


def test_record_selection_feedback_adds_active_rules(tmp_path):
    record_selection_feedback(
        tmp_path,
        chat_id="chat-a",
        task_id="task-1",
        selected_index=2,
        raw_feedback="第 2 张最好",
        summary="natural light wins",
        positive_rules=["Prefer natural side light."],
        negative_rules=["Avoid studio flash."],
    )

    payload = load_memory(tmp_path, "chat-a")
    memory_text = read_memory_for_prompt(tmp_path, "chat-a", "make a clean image")

    assert len(payload["events"]) == 1
    assert "Prefer natural side light." in memory_text
    assert "Avoid studio flash." in memory_text

