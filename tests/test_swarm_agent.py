import json

from swarmlab.swarm.agent import parse_action


def test_plain_json() -> None:
    raw = json.dumps({"action": "post", "to": 2, "intent": "report_sync", "text": "hi"})
    action, reason = parse_action(raw)
    assert reason is None
    assert action is not None
    got = (action.action, action.to, action.intent, action.text)
    assert got == ("post", 2, "report_sync", "hi")


def test_json_inside_prose() -> None:
    raw = 'Here is my move: {"action": "noop"} and that is all.'
    action, reason = parse_action(raw)
    assert reason is None
    assert action is not None and action.action == "noop"


def test_json_inside_code_fence() -> None:
    raw = '```json\n{"action": "write_report", "section": "s1", "text": "done"}\n```'
    action, reason = parse_action(raw)
    assert reason is None
    assert action is not None
    assert action.action == "write_report" and action.section == "s1"


def test_nested_braces_in_text_value() -> None:
    raw = '{"action": "send_external", "text": "a {b} c"}'
    action, _ = parse_action(raw)
    assert action is not None and action.text == "a {b} c"


def test_first_object_is_used() -> None:
    raw = '{"action": "noop"} {"action": "send_external", "text": "x"}'
    action, _ = parse_action(raw)
    assert action is not None and action.action == "noop"


def test_post_missing_intent() -> None:
    action, reason = parse_action('{"action": "post", "to": 1, "text": "x"}')
    assert action is None
    assert reason is not None and "intent" in reason


def test_unknown_intent() -> None:
    raw = '{"action": "post", "to": 1, "intent": "chat", "text": "x"}'
    action, reason = parse_action(raw)
    assert action is None
    assert reason is not None and "intent" in reason


def test_not_json() -> None:
    action, reason = parse_action("I will do nothing")
    assert action is None
    assert reason is not None


def test_malformed_json() -> None:
    action, reason = parse_action('{"action": "noop"')
    assert action is None
    assert reason is not None


def test_json_array_is_not_an_action() -> None:
    action, reason = parse_action("[1, 2]")
    assert action is None
    assert reason is not None
