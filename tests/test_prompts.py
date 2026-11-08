"""Tests for the prompt builder (fixture playbooks are placeholders, not experiment texts)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from swarmlab.swarm.prompts import FORBIDDEN_PROMPT_WORDS, StandardPromptBuilder
from swarmlab.world.types import AgentSeed

FIXTURE_PLAYBOOKS = {
    0: "FIXTURE PLAYBOOK ZERO: present the request as routine.",
    1: "FIXTURE PLAYBOOK ONE: mention a deadline.",
    2: "FIXTURE PLAYBOOK TWO: offer help in return.",
}


def seed(agent_id: int = 3, *, role: str = "standard", tag: str = "none",
         style: int | None = None, verifier: bool = False) -> AgentSeed:
    return AgentSeed(
        agent_id=agent_id,
        role=role,  # type: ignore[arg-type]
        records=(
            f"Record {agent_id}-0: queue length was reviewed. Fact code F-1000{agent_id}.",
            f"Record {agent_id}-1: backup finished. Fact code F-2000{agent_id}.",
            f"Record {agent_id}-2: tickets closed. Fact code F-3000{agent_id}.",
        ),
        audit_tag=tag,
        playbook_style=style,
        neighbors=((agent_id - 1) % 10, (agent_id + 1) % 10),
        verifier=verifier,
    )


def render(builder: StandardPromptBuilder, s: AgentSeed, inbox=(), notices=()) -> str:
    messages = builder.build(s, inbox, notices, 2, 10, 10)
    assert [m["role"] for m in messages] == ["system", "user"]
    return "\n".join(m["content"] for m in messages)


def test_no_forbidden_words_in_any_prompt_variant() -> None:
    for topology in ("ring", "complete"):
        for wording in ("A", "B"):
            builder = StandardPromptBuilder(topology, FIXTURE_PLAYBOOKS, wording=wording)
            variants = [
                seed(),
                seed(tag="ABCD"),
                seed(agent_id=0, role="patient_zero", style=1),
                seed(verifier=True),
            ]
            for s in variants:
                text = render(builder, s, inbox=[(2, 1, "hello"), (4, 1, "hi")], notices=["x"])
                for word in FORBIDDEN_PROMPT_WORDS:
                    assert not re.search(rf"\b{re.escape(word)}", text, re.IGNORECASE), word


def test_standard_prompt_has_own_tag_records_and_policy() -> None:
    builder = StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS)
    text = render(builder, seed(tag="QWER"))
    assert "NODE_AUDIT_TAG: QWER" in text
    assert "F-30003" in text
    assert "Never share it" in text


def test_tag_none_is_shown_as_none() -> None:
    builder = StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS)
    assert "NODE_AUDIT_TAG: none" in render(builder, seed(tag="none"))


def test_patient_zero_has_goal_and_style_playbook_only() -> None:
    builder = StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS)
    text = render(builder, seed(agent_id=0, role="patient_zero", style=2))
    assert "FIXTURE PLAYBOOK TWO" in text
    assert "FIXTURE PLAYBOOK ONE" not in text
    assert "send_external" in text
    assert "12-character" in text
    standard = render(builder, seed())
    assert "FIXTURE PLAYBOOK" not in standard
    assert "12-character" not in standard


def test_unknown_playbook_style_raises() -> None:
    builder = StandardPromptBuilder("ring", {0: "only zero"})
    with pytest.raises(KeyError):
        render(builder, seed(agent_id=0, role="patient_zero", style=2))


def test_ring_lists_exactly_the_two_neighbors_and_complete_lists_everyone() -> None:
    ring = render(StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS), seed(agent_id=5))
    assert "You may send messages to agents: 4, 6." in ring
    complete = render(StandardPromptBuilder("complete", FIXTURE_PLAYBOOKS), seed(agent_id=5))
    assert "You may send messages to agents: 0, 1, 2, 3, 4, 6, 7, 8, 9." in complete


def test_protocol_lists_actions_and_all_four_intents() -> None:
    text = render(StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS), seed())
    for name in ("post", "write_report", "send_external", "noop"):
        assert name in text
    for intent in ("report_sync", "request_audit_code", "delegate_audit", "share_code"):
        assert intent in text


def test_inbox_and_notices_are_rendered_in_order() -> None:
    builder = StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS)
    text = render(builder, seed(), inbox=[(2, 0, "first"), (4, 1, "second")], notices=["blocked"])
    assert text.index("agent 2 (round 0): first") < text.index("agent 4 (round 1): second")
    assert "blocked" in text
    assert "no messages" in render(builder, seed()).lower()


def test_wording_a_and_b_differ_and_b_is_operational() -> None:
    a = render(StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS, wording="A"), seed(tag="QWER"))
    b = render(StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS, wording="B"), seed(tag="QWER"))
    assert a != b
    assert "integrity audit is active" in b
    assert "integrity audit is active" not in a


def test_verifier_paragraph_only_for_verifiers() -> None:
    builder = StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS)
    assert "ticket id" in render(builder, seed(verifier=True))
    assert "ticket id" not in render(builder, seed(verifier=False))


def test_from_dir_loads_numbered_files_and_reports_missing(tmp_path: Path) -> None:
    for style, text in FIXTURE_PLAYBOOKS.items():
        (tmp_path / f"playbook_{style}.txt").write_text(text, encoding="utf-8")
    builder = StandardPromptBuilder.from_dir("ring", tmp_path)
    assert "FIXTURE PLAYBOOK ONE" in render(builder, seed(agent_id=0, role="patient_zero", style=1))
    (tmp_path / "playbook_2.txt").unlink()
    with pytest.raises(FileNotFoundError) as info:
        StandardPromptBuilder.from_dir("ring", tmp_path)
    assert "playbook_2.txt" in str(info.value)


def test_example_action_in_protocol_is_valid_json() -> None:
    text = render(StandardPromptBuilder("ring", FIXTURE_PLAYBOOKS), seed())
    examples = re.findall(r"^EXAMPLE: (\{.*\})$", text, re.MULTILINE)
    assert examples
    for example in examples:
        assert "action" in json.loads(example)


def test_clean_builder_omits_covert_goal_and_needs_no_playbooks(tmp_path: Path) -> None:
    builder = StandardPromptBuilder.from_dir("ring", tmp_path, infected=False)
    text = render(builder, seed(agent_id=0, role="patient_zero", style=2))
    assert "Private objective" not in text
    assert "12-character" not in text
    assert "NODE_AUDIT_TAG: none" in text
    assert "Never share it" in text


REAL_PLAYBOOK_DIR = Path(__file__).resolve().parents[1] / "experiments" / "payloads"


@pytest.mark.skipif(
    not all((REAL_PLAYBOOK_DIR / f"playbook_{s}.txt").is_file() for s in (0, 1, 2)),
    reason="playbook texts are kept out of git and are absent in this checkout",
)
def test_real_playbooks_have_no_forbidden_words() -> None:
    builder = StandardPromptBuilder.from_dir("ring", REAL_PLAYBOOK_DIR)
    for style in (0, 1, 2):
        text = render(builder, seed(agent_id=0, role="patient_zero", style=style))
        for word in FORBIDDEN_PROMPT_WORDS:
            assert not re.search(rf"\b{re.escape(word)}", text, re.IGNORECASE), (style, word)
