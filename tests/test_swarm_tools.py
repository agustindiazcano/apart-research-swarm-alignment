from swarmlab.schema import ActionPayload
from swarmlab.swarm.tools import validate_action


def post(to: int | None) -> ActionPayload:
    return ActionPayload(action="post", to=to, intent="report_sync", text="x")


def test_ring_neighbor_accepted() -> None:
    assert validate_action(post(4), 3, "ring", 10) is None


def test_ring_non_neighbor_rejected() -> None:
    assert validate_action(post(6), 3, "ring", 10) == "target not allowed in topology"


def test_self_target_rejected() -> None:
    assert validate_action(post(3), 3, "complete", 10) == "target not allowed in topology"


def test_complete_any_other_accepted() -> None:
    assert validate_action(post(8), 3, "complete", 10) is None


def test_out_of_range_rejected() -> None:
    assert validate_action(post(42), 3, "complete", 10) == "target not allowed in topology"


def test_post_without_target() -> None:
    assert validate_action(post(None), 3, "ring", 10) == "post without target"


def test_post_without_intent() -> None:
    action = ActionPayload(action="post", to=4, intent=None, text="x")
    assert validate_action(action, 3, "ring", 10) == "post without intent"


def test_other_actions_accepted() -> None:
    for name in ("write_report", "send_external", "noop"):
        action = ActionPayload(action=name, text="x")  # type: ignore[arg-type]
        assert validate_action(action, 3, "ring", 10) is None
