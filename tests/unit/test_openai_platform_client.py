from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import app.core.clients.openai_platform as openai_platform_module
from app.core.clients.openai_platform import OpenAIPlatformError, _iter_sse_event_blocks, fetch_models
from app.core.clients.proxy import pop_compact_timeout_overrides, push_compact_timeout_overrides
from app.core.utils.json_guards import is_json_mapping


class _FakeContent:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def iter_chunked(self, size: int):
        del size
        for chunk in self._chunks:
            yield chunk


class _FakeResponse:
    def __init__(
        self,
        chunks: list[bytes],
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        body: object | None = None,
        json_error: Exception | None = None,
        text_body: str | None = None,
    ) -> None:
        self.status = status
        self.headers = headers or {}
        self.content = _FakeContent(chunks)
        self._body = body
        self._json_error = json_error
        self._text_body = text_body
        self.released = False

    async def json(self, content_type=None):
        del content_type
        if self._json_error is not None:
            raise self._json_error
        return self._body

    async def read(self) -> bytes:
        if self._text_body is None:
            return b""
        return self._text_body.encode("utf-8")

    def release(self) -> None:
        self.released = True


class _ResponseContext:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    async def __aenter__(self) -> _FakeResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.get_calls: list[dict[str, object]] = []
        self.post_calls: list[dict[str, object]] = []

    def get(self, url: str, *, headers, timeout):
        self.get_calls.append(
            {
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return _ResponseContext(self._response)

    async def post(self, url: str, *, headers, json, timeout):
        self.post_calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return self._response


class _ContextPostSession:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.post_calls: list[dict[str, object]] = []

    def post(self, url: str, *, headers, json, timeout):
        self.post_calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return _ResponseContext(self._response)


@pytest.mark.asyncio
async def test_iter_sse_event_blocks_reassembles_fragmented_events() -> None:
    response = _FakeResponse(
        [
            b'event: response.output_text.delta\ndata: {"type":"response.output_text.delta"}',
            b"\n\n",
            (
                b"event: response.completed\ndata: "
                b'{"type":"response.completed","response":{"id":"resp_1","status":"completed"}}\n'
            ),
            b"\n",
        ]
    )

    events = [event async for event in _iter_sse_event_blocks(response)]

    assert events == [
        'event: response.output_text.delta\ndata: {"type":"response.output_text.delta"}\n\n',
        (
            "event: response.completed\ndata: "
            '{"type":"response.completed","response":{"id":"resp_1","status":"completed"}}\n\n'
        ),
    ]


@pytest.mark.asyncio
async def test_fetch_models_normalizes_non_json_error_body(monkeypatch) -> None:
    response = _FakeResponse(
        [],
        status=502,
        headers={"x-request-id": "up_req_models_error"},
        json_error=json.JSONDecodeError("bad json", "<html>upstream outage</html>", 0),
        text_body="<html>upstream outage</html>",
    )
    session = _FakeSession(response)
    monkeypatch.setattr(openai_platform_module, "get_http_client", lambda: SimpleNamespace(session=session))

    with pytest.raises(OpenAIPlatformError) as exc_info:
        await fetch_models(base_url="https://api.openai.com", api_key="sk-test")

    assert exc_info.value.status_code == 502
    error = exc_info.value.payload.get("error")
    assert is_json_mapping(error)
    assert error.get("code") == "platform_http_502"
    assert "upstream outage" in str(error.get("message"))
    assert exc_info.value.upstream_request_id == "up_req_models_error"
    assert session.get_calls[0]["url"] == "https://api.openai.com/v1/models"


@pytest.mark.asyncio
async def test_stream_responses_preserves_upstream_request_id(monkeypatch) -> None:
    response = _FakeResponse(
        [
            b'data: {"type":"response.created","response":{"id":"resp_1"}}\n\n',
            (b'data: {"type":"response.completed","response":{"id":"resp_1","status":"completed"}}\n\n'),
        ],
        headers={"x-request-id": "up_req_stream_1"},
    )
    session = _FakeSession(response)
    monkeypatch.setattr(openai_platform_module, "get_http_client", lambda: SimpleNamespace(session=session))

    stream_response = await openai_platform_module.stream_responses(
        base_url="https://api.openai.com",
        payload={"model": "gpt-5.1", "input": "hi"},
        api_key="sk-test",
        organization="org_test",
        project="proj_test",
    )
    events = [event async for event in stream_response.event_stream]

    assert stream_response.upstream_request_id == "up_req_stream_1"
    assert events == [
        'data: {"type":"response.created","response":{"id":"resp_1"}}\n\n',
        'data: {"type":"response.completed","response":{"id":"resp_1","status":"completed"}}\n\n',
    ]
    assert response.released is True
    assert session.post_calls[0]["url"] == "https://api.openai.com/v1/responses"


@pytest.mark.asyncio
async def test_create_compact_response_respects_compact_timeout_overrides(monkeypatch) -> None:
    response = _FakeResponse(
        [],
        body={
            "object": "response.compaction",
            "status": "completed",
            "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            "output": [],
        },
    )
    session = _ContextPostSession(response)
    monkeypatch.setattr(openai_platform_module, "get_http_client", lambda: SimpleNamespace(session=session))
    monkeypatch.setattr(
        openai_platform_module,
        "get_settings",
        lambda: SimpleNamespace(upstream_connect_timeout_seconds=8.0),
    )
    timeout_tokens = push_compact_timeout_overrides(connect_timeout_seconds=11.0, total_timeout_seconds=11.0)

    try:
        result = await openai_platform_module.create_compact_response(
            base_url="https://api.openai.com",
            payload={"model": "gpt-5.1", "input": "hi"},
            api_key="sk-test",
        )
    finally:
        pop_compact_timeout_overrides(timeout_tokens)

    timeout = session.post_calls[0]["timeout"]
    assert result.payload.object == "response.compaction"
    assert timeout.sock_connect == pytest.approx(8.0)
    assert timeout.total == pytest.approx(11.0, abs=0.01)


@pytest.mark.asyncio
async def test_create_compact_response_inlines_input_images(monkeypatch) -> None:
    response = _FakeResponse(
        [],
        body={
            "object": "response.compaction",
            "status": "completed",
            "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            "output": [],
        },
    )
    session = _ContextPostSession(response)
    captured: dict[str, object] = {}

    async def fake_inline(payload, *, session, connect_timeout, total_timeout):
        captured["payload"] = dict(payload)
        captured["session"] = session
        captured["connect_timeout"] = connect_timeout
        captured["total_timeout"] = total_timeout
        return {
            **dict(payload),
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": "data:image/png;base64,inline",
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr(openai_platform_module, "get_http_client", lambda: SimpleNamespace(session=session))
    monkeypatch.setattr(
        openai_platform_module,
        "get_settings",
        lambda: SimpleNamespace(upstream_connect_timeout_seconds=8.0),
    )
    monkeypatch.setattr(openai_platform_module, "maybe_inline_payload_input_images", fake_inline)

    result = await openai_platform_module.create_compact_response(
        base_url="https://api.openai.com",
        payload={
            "model": "gpt-5.1",
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": "https://example.com/image.png",
                        }
                    ],
                }
            ],
        },
        api_key="sk-test",
    )

    assert result.payload.object == "response.compaction"
    assert captured["connect_timeout"] == pytest.approx(8.0)
    assert captured["total_timeout"] is None
    assert session.post_calls[0]["json"]["input"][0]["content"][0]["image_url"].startswith("data:image/png")


@pytest.mark.asyncio
async def test_create_compact_response_deducts_inline_preprocessing_from_total_timeout(monkeypatch) -> None:
    response = _FakeResponse(
        [],
        body={
            "object": "response.compaction",
            "status": "completed",
            "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            "output": [],
        },
    )
    session = _ContextPostSession(response)
    monotonic_values = iter([100.0, 104.5])
    monkeypatch.setattr(openai_platform_module, "get_http_client", lambda: SimpleNamespace(session=session))
    monkeypatch.setattr(
        openai_platform_module,
        "get_settings",
        lambda: SimpleNamespace(upstream_connect_timeout_seconds=8.0),
    )
    monkeypatch.setattr(openai_platform_module.time, "monotonic", lambda: next(monotonic_values, 104.5))
    timeout_tokens = push_compact_timeout_overrides(connect_timeout_seconds=8.0, total_timeout_seconds=10.0)

    try:
        result = await openai_platform_module.create_compact_response(
            base_url="https://api.openai.com",
            payload={"model": "gpt-5.1", "input": "hi"},
            api_key="sk-test",
        )
    finally:
        pop_compact_timeout_overrides(timeout_tokens)

    timeout = session.post_calls[0]["timeout"]
    assert result.payload.object == "response.compaction"
    assert timeout.total == pytest.approx(5.5)
    assert timeout.sock_read == pytest.approx(5.5)
    assert timeout.sock_connect == pytest.approx(5.5)


@pytest.mark.asyncio
async def test_create_response_preserves_upstream_request_id_on_error(monkeypatch) -> None:
    response = _FakeResponse(
        [],
        status=401,
        headers={"x-request-id": "up_req_platform_error"},
        body={"error": {"code": "invalid_api_key", "message": "Invalid API key"}},
    )
    session = _ContextPostSession(response)
    monkeypatch.setattr(openai_platform_module, "get_http_client", lambda: SimpleNamespace(session=session))

    with pytest.raises(OpenAIPlatformError) as exc_info:
        await openai_platform_module.create_response(
            base_url="https://api.openai.com",
            payload={"model": "gpt-5.1", "input": "hi"},
            api_key="sk-test",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.upstream_request_id == "up_req_platform_error"
