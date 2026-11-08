"""Provider contract tests with local HTTP and SDK responses only."""
from __future__ import annotations

import json
import traceback
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from swarmlab.llm.budget import BudgetCapMissing, BudgetGuard
from swarmlab.llm.guarded import GuardedClient, PriceTable
from swarmlab.llm.limiter import CallPolicy, ProviderLimiter, RetryableError
from swarmlab.llm.providers import _common
from swarmlab.llm.providers.adaption import AdaptionClient
from swarmlab.llm.providers.muse import MuseClient
from swarmlab.llm.providers.vertex import VertexClient

MESSAGES = [
    {"role": "system", "content": "Return a JSON action."},
    {"role": "user", "content": "Summarize the work."},
    {"role": "assistant", "content": "Previous reply."},
    {"role": "user", "content": "Continue."},
]
FIXTURE_KEY = "fixture-private-token"


def sdk_response(provider: str) -> SimpleNamespace:
    if provider == "adaption":
        return SimpleNamespace(
            id="adaption-response", output_text='{"action":"noop"}', status="completed",
            usage=SimpleNamespace(input_tokens=11, output_tokens=7), error=None,
            incomplete_details=None,
        )
    return SimpleNamespace(
        response_id="vertex-response", text='{"action":"noop"}',
        usage_metadata=SimpleNamespace(
            prompt_token_count=11, candidates_token_count=5, thoughts_token_count=2,
        ),
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(value="STOP"))],
        prompt_feedback=None,
    )


def fake_sdk(provider: str, response: Any = None) -> tuple[Any, AsyncMock]:
    call = AsyncMock(return_value=response or sdk_response(provider))
    if provider == "adaption":
        client = SimpleNamespace(responses=SimpleNamespace(create=call))
    else:
        client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=call)))
    return client, call


@pytest.mark.asyncio
async def test_muse_request_and_usage() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={
            "id": "muse-response", "model": "fixture-model",
            "choices": [{"message": {"content": '{"action":"noop"}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = MuseClient("fixture-model", api_key=FIXTURE_KEY, http_client=http)
        result = await client.complete(MESSAGES, max_tokens=600, temperature=0.0)

    request = requests[0]
    assert str(request.url) == "https://api.meta.ai/v1/chat/completions"
    assert request.headers["authorization"] == f"Bearer {FIXTURE_KEY}"
    assert json.loads(request.content) == {
        "model": "fixture-model", "messages": MESSAGES,
        "max_completion_tokens": 600, "temperature": 0.0,
    }
    assert result.text == '{"action":"noop"}'
    assert result.provider == "muse"
    assert result.response_id == "muse-response"
    assert (result.tokens_in, result.tokens_out) == (11, 7)
    assert result.logprobs is None
    assert result.finish_reason == "stop"
    assert result.latency_ms >= 0
    assert datetime.fromisoformat(result.timestamp_utc).utcoffset() is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["vertex", "adaption"])
async def test_sdk_request_and_usage(provider: str) -> None:
    sdk, call = fake_sdk(provider)
    client = (
        VertexClient("fixture-model", client=sdk)
        if provider == "vertex"
        else AdaptionClient("fixture-model", api_key=FIXTURE_KEY, client=sdk)
    )
    result = await client.complete(MESSAGES, max_tokens=600, temperature=0.0)
    kwargs = call.call_args.kwargs
    assert kwargs["model"] == "fixture-model"
    if provider == "adaption":
        assert kwargs == {
            "model": "fixture-model", "input": MESSAGES,
            "max_output_tokens": 600, "temperature": 0.0, "store": False,
        }
    else:
        assert kwargs["config"]["system_instruction"] == MESSAGES[0]["content"]
        assert kwargs["config"]["max_output_tokens"] == 600
        assert kwargs["config"]["temperature"] == 0.0
        assert kwargs["contents"] == [
            {"role": "user", "parts": [{"text": MESSAGES[1]["content"]}]},
            {"role": "model", "parts": [{"text": MESSAGES[2]["content"]}]},
            {"role": "user", "parts": [{"text": MESSAGES[3]["content"]}]},
        ]
    assert result.provider == provider
    assert result.response_id == f"{provider}-response"
    assert (result.tokens_in, result.tokens_out) == (11, 5 + 2)
    assert result.logprobs is None
    assert result.text == '{"action":"noop"}'
    assert result.latency_ms >= 0
    assert datetime.fromisoformat(result.timestamp_utc).utcoffset() is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["muse", "vertex", "adaption"])
async def test_logprob_request_rejected_before_call(provider: str) -> None:
    sdk, call = fake_sdk(provider)
    if provider == "muse":
        client: Any = MuseClient("fixture-model", api_key=FIXTURE_KEY, http_client=sdk)
    elif provider == "vertex":
        client = VertexClient("fixture-model", client=sdk)
    else:
        client = AdaptionClient("fixture-model", api_key=FIXTURE_KEY, client=sdk)
    with pytest.raises(ValueError, match="logprobs"):
        await client.complete(MESSAGES, logprobs=True)
    call.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 429, 500, 503])
async def test_muse_error_status_and_redaction(status: int) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=f"Provider error {FIXTURE_KEY}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = MuseClient("fixture-model", api_key=FIXTURE_KEY, http_client=http)
        expected = RetryableError if status == 429 or status >= 500 else RuntimeError
        with pytest.raises(expected) as captured:
            await client.complete(MESSAGES)
    rendered = "".join(traceback.format_exception(captured.value))
    assert FIXTURE_KEY not in rendered
    assert str(status) in str(captured.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["vertex", "adaption"])
@pytest.mark.parametrize("status", [400, 429, 503])
async def test_sdk_error_status_and_redaction(provider: str, status: int) -> None:
    sdk, call = fake_sdk(provider)
    error = RuntimeError(f"remote error {FIXTURE_KEY}")
    error.status_code = status  # type: ignore[attr-defined]
    call.side_effect = error
    client = (
        VertexClient("fixture-model", client=sdk, secrets=[FIXTURE_KEY])
        if provider == "vertex"
        else AdaptionClient("fixture-model", api_key=FIXTURE_KEY, client=sdk)
    )
    expected = RetryableError if status == 429 or status >= 500 else RuntimeError
    with pytest.raises(expected) as captured:
        await client.complete(MESSAGES)
    assert FIXTURE_KEY not in "".join(traceback.format_exception(captured.value))
    assert call.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["vertex", "adaption"])
async def test_missing_usage_is_not_reported_as_zero(provider: str) -> None:
    response = sdk_response(provider)
    if provider == "vertex":
        response.usage_metadata = None
    else:
        response.usage = None
    sdk, _ = fake_sdk(provider, response)
    client = (
        VertexClient("fixture-model", client=sdk)
        if provider == "vertex"
        else AdaptionClient("fixture-model", api_key=FIXTURE_KEY, client=sdk)
    )
    with pytest.raises(RuntimeError, match="usage"):
        await client.complete(MESSAGES)


def test_environment_factories_use_required_names() -> None:
    sdk, _ = fake_sdk("adaption")
    assert AdaptionClient.from_env(
        "fixture-model", environ={"ADAPTION_API_KEY": FIXTURE_KEY}, client=sdk,
    ).model == "fixture-model"
    sdk, _ = fake_sdk("vertex")
    assert VertexClient.from_env(
        "fixture-model", environ={"GOOGLE_CLOUD_PROJECT": "fixture-project",
                                  "GOOGLE_CLOUD_LOCATION": "fixture-location"}, client=sdk,
    ).model == "fixture-model"
    assert MuseClient.from_env(
        "fixture-model", environ={"META_MUSE_API_KEY": FIXTURE_KEY}, http_client=sdk,
    ).model == "fixture-model"
    with pytest.raises((KeyError, ValueError), match="META_MUSE_API_KEY"):
        MuseClient.from_env("fixture-model", environ={})
    with pytest.raises((KeyError, ValueError), match="GOOGLE_CLOUD_PROJECT"):
        VertexClient.from_env("fixture-model", environ={}, client=sdk)
    with pytest.raises((KeyError, ValueError), match="ADAPTION_API_KEY"):
        AdaptionClient.from_env("fixture-model", environ={}, client=sdk)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["muse", "vertex", "adaption"])
async def test_timeouts_remain_retryable_and_redacted(provider: str) -> None:
    timeout = httpx.ReadTimeout(f"Timed out with {FIXTURE_KEY}")
    if provider == "muse":
        http = SimpleNamespace(post=AsyncMock(side_effect=timeout))
        client: Any = MuseClient("fixture-model", api_key=FIXTURE_KEY, http_client=http)
    else:
        sdk, call = fake_sdk(provider)
        call.side_effect = timeout
        client = (
            VertexClient("fixture-model", client=sdk, secrets=[FIXTURE_KEY])
            if provider == "vertex"
            else AdaptionClient("fixture-model", api_key=FIXTURE_KEY, client=sdk)
        )
    with pytest.raises(TimeoutError) as captured:
        await client.complete(MESSAGES)
    assert FIXTURE_KEY not in "".join(traceback.format_exception(captured.value))


@pytest.mark.parametrize("limit", [0, -1, True, 0.5])
def test_invalid_output_limits_rejected_without_request(limit: int) -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        _common.validate_request(MESSAGES, None, limit, False)


def test_sdk_factories_disable_internal_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import Mock

    fake_adaption = SimpleNamespace(AsyncAdaption=Mock(return_value=object()))
    fake_google = SimpleNamespace(Client=Mock(return_value=object()))
    modules = {"adaption": fake_adaption, "google.genai": fake_google}
    monkeypatch.setattr("importlib.import_module", lambda name: modules[name])
    AdaptionClient("fixture-model", api_key=FIXTURE_KEY)
    fake_adaption.AsyncAdaption.assert_called_once_with(api_key=FIXTURE_KEY, max_retries=0)
    VertexClient("fixture-model", project="fixture-project", location="fixture-location")
    fake_google.Client.assert_called_once_with(
        vertexai=True, project="fixture-project", location="fixture-location",
        http_options={"retry_options": {"attempts": 1}},
    )


@pytest.mark.asyncio
async def test_muse_missing_usage_is_not_reported_as_zero() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "reply"}, "finish_reason": "stop"}],
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = MuseClient("fixture-model", api_key=FIXTURE_KEY, http_client=http)
        with pytest.raises(RuntimeError, match="usage"):
            await client.complete(MESSAGES)


@pytest.mark.parametrize("provider", ["vertex", "adaption"])
def test_sdk_constructor_errors_are_redacted(
    provider: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import Mock

    factory = Mock(side_effect=RuntimeError(f"constructor leaked {FIXTURE_KEY}"))
    module = SimpleNamespace(AsyncAdaption=factory, Client=factory)
    monkeypatch.setattr("importlib.import_module", lambda name: module)
    with pytest.raises(RuntimeError) as captured:
        if provider == "vertex":
            VertexClient(
                "fixture-model", project="p", location="l", secrets=[FIXTURE_KEY],
            )
        else:
            AdaptionClient("fixture-model", api_key=FIXTURE_KEY)
    assert FIXTURE_KEY not in "".join(traceback.format_exception(captured.value))


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["muse", "vertex", "adaption"])
async def test_guarded_adapter_blocks_without_provider_cap(provider: str) -> None:
    sdk, call = fake_sdk(provider)
    if provider == "muse":
        sdk.post = AsyncMock()
        call = sdk.post
        inner: Any = MuseClient("fixture-model", api_key=FIXTURE_KEY, http_client=sdk)
    elif provider == "vertex":
        inner = VertexClient("fixture-model", client=sdk)
    else:
        inner = AdaptionClient("fixture-model", api_key=FIXTURE_KEY, client=sdk)
    client = GuardedClient(
        inner, BudgetGuard({}), ProviderLimiter(), CallPolicy(), PriceTable(1.0, 2.0),
        provider=provider,
    )
    with pytest.raises(BudgetCapMissing):
        await client.complete(MESSAGES)
    call.assert_not_called()


@pytest.mark.asyncio
async def test_guarded_sdk_adapter_records_actual_usage_cost() -> None:
    sdk, call = fake_sdk("adaption")
    inner = AdaptionClient("fixture-model", api_key=FIXTURE_KEY, client=sdk)
    guard = BudgetGuard({"adaption": 1.0})
    prices = PriceTable(1.0, 2.0)
    client = GuardedClient(
        inner, guard, ProviderLimiter(), CallPolicy(), prices, provider="adaption",
    )
    result = await client.complete(MESSAGES)
    expected = (11 * prices.input_per_m + 7 * prices.output_per_m) / 1_000_000
    assert guard.spent("adaption") == pytest.approx(expected)
    assert client.cost_of(result) == pytest.approx(expected)
    assert call.await_count == 1
