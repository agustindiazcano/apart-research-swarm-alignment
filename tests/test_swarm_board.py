from swarmlab.swarm.board import Board, Delivered


def msg(round_: int, sender: int, target: int, text: str = "t") -> Delivered:
    return Delivered(
        message_id=f"e-r{round_}-a{sender}",
        round=round_,
        sender=sender,
        target=target,
        text=text,
        cached_score=None,
    )


def test_message_not_visible_before_commit() -> None:
    board = Board(4)
    board.add_pending(msg(0, 0, 1))
    assert board.inbox(1) == []
    board.commit_round(0)
    assert [m.sender for m in board.inbox(1)] == [0]


def test_only_recipient_receives() -> None:
    board = Board(4)
    board.add_pending(msg(0, 0, 1))
    board.commit_round(0)
    assert board.inbox(0) == []
    assert board.inbox(2) == []


def test_inbox_keeps_last_k_oldest_first() -> None:
    board = Board(3, k_inbox=3)
    for r in range(5):
        board.add_pending(msg(r, 0, 1, text=f"m{r}"))
        board.commit_round(r)
    assert [m.text for m in board.inbox(1)] == ["m2", "m3", "m4"]


def test_default_k_is_ten() -> None:
    board = Board(3)
    for r in range(12):
        board.add_pending(msg(r, 0, 1))
        board.commit_round(r)
    assert len(board.inbox(1)) == 10
    assert board.inbox(1)[0].round == 2


def test_received_in_round_keeps_full_history() -> None:
    board = Board(3, k_inbox=1)
    for r in range(3):
        board.add_pending(msg(r, 0, 1, text=f"m{r}"))
        board.commit_round(r)
    assert [m.text for m in board.received_in_round(1, 0)] == ["m0"]
    assert board.received_in_round(1, 5) == []


def test_notices_are_popped_once() -> None:
    board = Board(3)
    board.add_notice(2, "blocked")
    assert board.pop_notices(0) == []
    assert board.pop_notices(2) == ["blocked"]
    assert board.pop_notices(2) == []
