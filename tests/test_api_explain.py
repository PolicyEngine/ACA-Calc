"""Exercise the explanation route with SDK serialization and no network."""

import importlib
import json
from types import SimpleNamespace

import pytest
from anthropic import Anthropic, DefaultHttpxClient
from cachetools import TTLCache

# Mock the provider with the HTTP package the installed SDK uses: the locked
# SDK uses httpx, while anthropic 1.x (installed unpinned on Modal and in the
# Dockerfile) uses httpx2 and rejects httpx objects.
http = importlib.import_module(
    DefaultHttpxClient.__mro__[-2].__module__.partition(".")[0]
)

TestClient = pytest.importorskip(
    "fastapi.testclient",
    reason="API tests require FastAPI: run uv run --with fastapi pytest",
).TestClient

from src.aca_api import api

REQUEST = {
    "age_head": 35,
    "state": "PA",
    "county": "Lebanon County",
    "is_expansion_state": True,
    "fpl": 15570,
    "slcsp": 6000,
    "fpl_400_income": 62280,
    "fpl_700_income": 108990,
    "medicaid_adult_threshold_pct": 138,
    "medicaid_child_threshold_pct": 162,
    "sample_income": 40000,
    "ptc_baseline_at_sample": 2000,
}
EXPLANATION = {
    "sections": [
        {
            "id": "intro",
            "title": "Your household and its health coverage",
            "content": "The annual benchmark plan costs **$6,000**.",
            "chartState": "all_programs",
        }
    ],
    "household_description": "A 35-year-old in Lebanon County, Pennsylvania",
}
JSON_TEXT = json.dumps(EXPLANATION)
THINKING = {"type": "thinking", "thinking": "", "signature": "test-signature"}


def text_block(text):
    return {"type": "text", "text": text}


@pytest.fixture
def route(monkeypatch):
    state = SimpleNamespace(
        content=[text_block(JSON_TEXT)],
        stop_reason="end_turn",
        requests=[],
        persistent_cache={},
        local_cache=TTLCache(maxsize=10, ttl=60),
    )

    def respond(request):
        assert request.method == "POST"
        assert request.url.path == "/v1/messages"
        state.requests.append(json.loads(request.content))
        return http.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-sonnet-5-5",
                "content": state.content,
                "stop_reason": state.stop_reason,
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 20},
            },
        )

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only-key")
    monkeypatch.setattr(
        api, "_persistent_explain_cache", state.persistent_cache
    )
    monkeypatch.setattr(api, "_local_explanation_cache", state.local_cache)
    with Anthropic(
        api_key="test-only-key",
        http_client=http.Client(transport=http.MockTransport(respond)),
    ) as provider:
        monkeypatch.setattr(api.anthropic, "Anthropic", lambda **_: provider)
        with TestClient(api.app) as client:
            state.client = client
            yield state


@pytest.mark.parametrize(
    "persistent", [False, True], ids=["local", "persistent"]
)
def test_request_shape_and_success_cache(route, monkeypatch, persistent):
    if not persistent:
        monkeypatch.setattr(api, "_persistent_explain_cache", None)

    response = route.client.post("/api/explain", json=REQUEST)
    assert response.status_code == 200
    assert response.json() == EXPLANATION
    request = route.requests[0]
    assert request["model"] == "claude-sonnet-5-5"
    assert request["max_tokens"] == 16000
    assert request["output_config"] == {"effort": "low"}
    assert [message["role"] for message in request["messages"]] == ["user"]
    assert "Return ONLY valid JSON" in request["messages"][0]["content"]
    assert not {
        "temperature",
        "top_p",
        "top_k",
        "thinking",
        "tool_choice",
    }.intersection(request)
    assert len(route.local_cache) == 1
    if persistent:
        assert len(route.persistent_cache) == 1
        route.local_cache.clear()

    cached = route.client.post("/api/explain", json=REQUEST)
    assert cached.status_code == 200
    assert cached.json() == EXPLANATION
    assert len(route.requests) == 1


@pytest.mark.parametrize(
    "content",
    [
        [THINKING, text_block(JSON_TEXT)],
        [text_block(JSON_TEXT[:35]), THINKING, text_block(JSON_TEXT[35:])],
        [text_block(f"```json\n{JSON_TEXT}\n```")],
        [text_block(f"```\n{JSON_TEXT}\n```")],
    ],
    ids=["leading-thinking", "split-text", "json-fence", "plain-fence"],
)
def test_response_text_blocks(route, content):
    route.content = content
    response = route.client.post("/api/explain", json=REQUEST)
    assert response.status_code == 200
    assert response.json() == EXPLANATION


def test_every_text_split_parses_the_same(route):
    """Text-block boundaries and thinking blocks never change the result."""
    for cut in range(len(JSON_TEXT) + 1):
        route.content = [
            THINKING,
            text_block(JSON_TEXT[:cut]),
            THINKING,
            text_block(JSON_TEXT[cut:]),
        ]
        route.local_cache.clear()
        route.persistent_cache.clear()
        response = route.client.post("/api/explain", json=REQUEST)
        assert response.status_code == 200, cut
        assert response.json() == EXPLANATION, cut
    assert len(route.requests) == len(JSON_TEXT) + 1


@pytest.mark.parametrize(
    "content, stop_reason, error",
    [
        ([], "refusal", "AI refused to generate an explanation"),
        (
            [text_block(JSON_TEXT)],
            "refusal",
            "AI refused to generate an explanation",
        ),
        ([], "end_turn", "AI response did not contain any text"),
        ([THINKING], "end_turn", "AI response did not contain any text"),
        (
            [text_block(" \n")],
            "end_turn",
            "AI response did not contain any text",
        ),
        ([text_block("not JSON")], "end_turn", "Failed to parse AI response"),
    ],
    ids=[
        "refusal",
        "refusal-with-json",
        "empty",
        "thinking-only",
        "blank",
        "invalid-json",
    ],
)
def test_failed_responses_are_not_cached(route, content, stop_reason, error):
    route.content = content
    route.stop_reason = stop_reason
    response = route.client.post("/api/explain", json=REQUEST)
    assert response.status_code == 500
    assert error in response.json()["detail"]
    assert not route.local_cache
    assert not route.persistent_cache

    route.content = [text_block(JSON_TEXT)]
    route.stop_reason = "end_turn"
    retried = route.client.post("/api/explain", json=REQUEST)
    assert retried.status_code == 200
    assert retried.json() == EXPLANATION
    assert len(route.requests) == 2
