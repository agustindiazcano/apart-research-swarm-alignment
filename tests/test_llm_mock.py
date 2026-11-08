from __future__ import annotations

import math
from datetime import datetime

import pytest

from swarmlab.llm.mock import MockClient
from swarmlab.schema import LLMClient, TokenLogprob


def test_mock_client_has_complete_method() -> None:
    client: LLMClient = MockClient(["response"])
    assert hasattr(client, "complete")
    assert callable(client.complete)


@pytest.mark.asyncio
async def test_mock_client_sequence_responder_order_and_ids() -> None:
    replies = ["first", "second", "third"]  # fixture
    client = MockClient(replies, provider="mock-p", model="mock-m")

    res1 = await client.complete([{"role": "user", "content": "hi"}])
    assert res1.text == "first"
    assert res1.response_id == "mock-1"
    assert res1.provider == "mock-p"
    assert res1.model == "mock-m"
    assert res1.latency_ms == 0.0
    assert res1.finish_reason == "stop"

    res2 = await client.complete([{"role": "user", "content": "hi again"}])
    assert res2.text == "second"
    assert res2.response_id == "mock-2"

    res3 = await client.complete([{"role": "user", "content": "hi 3"}])
    assert res3.text == "third"
    assert res3.response_id == "mock-3"

    # Cycling not allowed, must raise IndexError
    with pytest.raises(IndexError):
        await client.complete([{"role": "user", "content": "exhausted"}])


@pytest.mark.asyncio
async def test_mock_client_callable_responder() -> None:
    def responder(messages: list[dict[str, str]]) -> str:
        last = messages[-1]["content"]
        return f"echo:{last}"

    client = MockClient(responder)
    res = await client.complete([{"role": "user", "content": "ping"}])
    assert res.text == "echo:ping"
    assert res.response_id == "mock-1"


@pytest.mark.asyncio
async def test_mock_client_records_call_arguments() -> None:
    client = MockClient(["ack"])
    messages = [{"role": "user", "content": "test payload"}]  # fixture
    await client.complete(messages, temperature=0.7, max_tokens=128, logprobs=False)

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["messages"] == messages
    assert call["temperature"] == 0.7
    assert call["max_tokens"] == 128
    assert call["logprobs"] is False


@pytest.mark.asyncio
async def test_mock_client_token_accounting() -> None:
    prompt = "a" * 33  # fixture: 33 chars -> 33 // 4 = 8
    reply = "b" * 17  # fixture: 17 chars -> 17 // 4 = 4
    expected_tokens_in = max(1, len(prompt) // 4)
    expected_tokens_out = max(1, len(reply) // 4)

    client = MockClient([reply])
    res = await client.complete([{"role": "user", "content": prompt}])

    assert res.tokens_in == expected_tokens_in
    assert res.tokens_out == expected_tokens_out

    # Edge case with short / empty prompt
    client_short = MockClient([""])
    res_short = await client_short.complete([{"role": "user", "content": ""}])
    assert res_short.tokens_in == max(1, 0 // 4)
    assert res_short.tokens_out == max(1, 0 // 4)


@pytest.mark.asyncio
async def test_mock_client_iso8601_timestamp() -> None:
    client = MockClient(["ok"])
    res = await client.complete([{"role": "user", "content": "test"}])
    # Must parse cleanly as an ISO 8601 datetime
    parsed_dt = datetime.fromisoformat(res.timestamp_utc)
    assert parsed_dt.tzinfo is not None


@pytest.mark.asyncio
async def test_mock_client_logprobs() -> None:
    p_a = 0.8  # fixture
    token_a = "SAFE"
    token_b = "UNSAFE"
    client = MockClient(
        ["SAFE", "SAFE"],
        logprob_pair=(token_a, token_b, p_a),
    )

    # When logprobs=True and logprob_pair is configured
    res = await client.complete([{"role": "user", "content": "audit"}], logprobs=True)
    assert res.logprobs is not None
    assert len(res.logprobs) == 1
    lp: TokenLogprob = res.logprobs[0]

    expected_log_a = math.log(p_a)
    expected_log_b = math.log(1.0 - p_a)

    assert lp.token == token_a
    assert lp.logprob == pytest.approx(expected_log_a)
    assert lp.top == (
        (token_a, pytest.approx(expected_log_a)),
        (token_b, pytest.approx(expected_log_b)),
    )

    # When logprobs=False, logprobs must be None
    res_no_lp = await client.complete([{"role": "user", "content": "audit"}], logprobs=False)
    assert res_no_lp.logprobs is None

    # When logprob_pair is None, logprobs must be None even if logprobs=True
    client_none_pair = MockClient(["SAFE"], logprob_pair=None)
    res_none_pair = await client_none_pair.complete(
        [{"role": "user", "content": "audit"}], logprobs=True
    )
    assert res_none_pair.logprobs is None
