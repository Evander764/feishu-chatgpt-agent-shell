from feishu_chatgpt_agent_shell.lark import build_gallery_card, extract_text_content, parse_lark_event


def test_gallery_card_contains_all_images():
    card = build_gallery_card("done", ["img_1", "img_2"], note="hello")

    assert card["header"]["title"]["content"] == "done"
    image_elements = [item for item in card["elements"] if item["tag"] == "img"]
    assert [item["img_key"] for item in image_elements] == ["img_1", "img_2"]


def test_parse_url_verification():
    parsed = parse_lark_event(
        {"type": "url_verification", "token": "tok", "challenge": "abc"},
        verification_token="tok",
    )

    assert parsed == {"challenge": "abc"}


def test_extract_text_content():
    assert extract_text_content('{"text":"hello"}') == "hello"

