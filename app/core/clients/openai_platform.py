from __future__ import annotations

import time
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Protocol, cast

import aiohttp

from app.core.clients.http import get_http_client
from app.core.clients.proxy import (
    as_image_fetch_session,
    current_compact_timeout_settings,
    maybe_inline_payload_input_images,
)
from app.core.config.settings import get_settings
from app.core.errors import openai_error
from app.core.openai.models import CompactResponsePayload, OpenAIResponsePayload
from app.core.openai.parsing import (
    parse_compact_response_payload,
    parse_error_payload,
    parse_response_payload,
)
from app.core.types import JsonValue
from app.core.utils.json_guards import is_json_dict
from app.core.utils.request_id import get_request_id
from app.core.utils.sse import format_sse_event

_MODELS_TIMEOUT_SECONDS = 15.0
_RESPONSES_TIMEOUT_SECONDS = 600.0


@dataclass(frozen=True, slots=True)
class PlatformModelsResponse:
    payload: dict[str, JsonValue]
    upstream_request_id: str | None


@dataclass(frozen=True, slots=True)
class PlatformResponseResult:
    payload: OpenAIResponsePayload | dict[str, JsonValue]
    upstream_request_id: str | None


@dataclass(frozen=True, slots=True)
class PlatformCompactResponseResult:
    payload: CompactResponsePayload
    upstream_request_id: str | None


@dataclass(frozen=True, slots=True)
class PlatformStreamResponse:
    event_stream: AsyncIterator[str]
    upstream_request_id: str | None


class OpenAIPlatformError(Exception):
    def __init__(
        self,
        status_code: int,
        payload: dict[str, JsonValue],
        *,
        upstream_request_id: str | None = None,
    ) -> None:
        super().__init__(f"OpenAI Platform request failed with status {status_code}")
        self.status_code = status_code
        self.payload = payload
        self.upstream_request_id = upstream_request_id


class _ChunkedContent(Protocol):
    def iter_chunked(self, size: int) -> AsyncIterator[bytes]: ...


class _ChunkedResponse(Protocol):
    content: _ChunkedContent


def build_platform_headers(
    api_key: str,
    *,
    organization: str | None = None,
    project: str | None = None,
    request_id: str | None = None,
    accept: str = "application/json",
) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": accept,
    }
    if organization:
        headers["OpenAI-Organization"] = organization
    if project:
        headers["OpenAI-Project"] = project
    resolved_request_id = request_id or get_request_id()
    if resolved_request_id:
        headers["x-request-id"] = resolved_request_id
    return headers


async def validate_platform_identity(
    *,
    base_url: str,
    api_key: str,
    organization: str | None = None,
    project: str | None = None,
) -> PlatformModelsResponse:
    return await fetch_models(
        base_url=base_url,
        api_key=api_key,
        organization=organization,
        project=project,
    )


async def fetch_models(
    *,
    base_url: str,
    api_key: str,
    organization: str | None = None,
    project: str | None = None,
) -> PlatformModelsResponse:
    url = f"{base_url.rstrip('/')}/v1/models"
    headers = build_platform_headers(api_key, organization=organization, project=project)
    timeout = aiohttp.ClientTimeout(total=_MODELS_TIMEOUT_SECONDS)
    session = get_http_client().session
    async with session.get(url, headers=headers, timeout=timeout) as response:
        payload = await _read_response_body(response)
        if response.status >= 400:
            raise OpenAIPlatformError(
                response.status,
                _normalize_error_payload(payload, response.status),
                upstream_request_id=response.headers.get("x-request-id"),
            )
        if not is_json_dict(payload):
            raise OpenAIPlatformError(
                502,
                _server_error("invalid_platform_models_response"),
                upstream_request_id=response.headers.get("x-request-id"),
            )
        return PlatformModelsResponse(
            payload=payload,
            upstream_request_id=response.headers.get("x-request-id"),
        )


async def create_response(
    *,
    base_url: str,
    payload: Mapping[str, JsonValue],
    api_key: str,
    organization: str | None = None,
    project: str | None = None,
) -> PlatformResponseResult:
    url = f"{base_url.rstrip('/')}/v1/responses"
    headers = build_platform_headers(api_key, organization=organization, project=project)
    timeout = aiohttp.ClientTimeout(total=_RESPONSES_TIMEOUT_SECONDS)
    session = get_http_client().session
    async with session.post(url, headers=headers, json=dict(payload), timeout=timeout) as response:
        body = await _read_response_body(response)
        if response.status >= 400:
            raise OpenAIPlatformError(
                response.status,
                _normalize_error_payload(body, response.status),
                upstream_request_id=response.headers.get("x-request-id"),
            )
        parsed = parse_response_payload(body)
        if parsed is None:
            if is_json_dict(body):
                return PlatformResponseResult(payload=body, upstream_request_id=response.headers.get("x-request-id"))
            raise OpenAIPlatformError(
                502,
                _server_error("invalid_platform_response"),
                upstream_request_id=response.headers.get("x-request-id"),
            )
        return PlatformResponseResult(payload=parsed, upstream_request_id=response.headers.get("x-request-id"))


async def create_compact_response(
    *,
    base_url: str,
    payload: Mapping[str, JsonValue],
    api_key: str,
    organization: str | None = None,
    project: str | None = None,
) -> PlatformCompactResponseResult:
    url = f"{base_url.rstrip('/')}/v1/responses/compact"
    headers = build_platform_headers(api_key, organization=organization, project=project)
    settings = get_settings()
    request_started_at = time.monotonic()
    connect_timeout, total_timeout = current_compact_timeout_settings(
        configured_connect_timeout_seconds=settings.upstream_connect_timeout_seconds,
        configured_total_timeout_seconds=None,
    )
    session = get_http_client().session
    payload_dict = await maybe_inline_payload_input_images(
        dict(payload),
        session=as_image_fetch_session(session),
        connect_timeout=connect_timeout,
        total_timeout=total_timeout,
    )
    effective_total_timeout = total_timeout
    if effective_total_timeout is not None:
        effective_total_timeout = max(0.001, effective_total_timeout - (time.monotonic() - request_started_at))
    effective_connect_timeout = connect_timeout
    if effective_total_timeout is not None:
        effective_connect_timeout = min(effective_connect_timeout, effective_total_timeout)
    timeout = aiohttp.ClientTimeout(
        total=effective_total_timeout,
        sock_connect=effective_connect_timeout,
        sock_read=effective_total_timeout,
    )
    async with session.post(url, headers=headers, json=payload_dict, timeout=timeout) as response:
        body = await _read_response_body(response)
        if response.status >= 400:
            raise OpenAIPlatformError(
                response.status,
                _normalize_error_payload(body, response.status),
                upstream_request_id=response.headers.get("x-request-id"),
            )
        parsed = parse_compact_response_payload(body)
        if parsed is None:
            raise OpenAIPlatformError(
                502,
                _server_error("invalid_platform_compact_response"),
                upstream_request_id=response.headers.get("x-request-id"),
            )
        return PlatformCompactResponseResult(
            payload=parsed,
            upstream_request_id=response.headers.get("x-request-id"),
        )


async def stream_responses(
    *,
    base_url: str,
    payload: Mapping[str, JsonValue],
    api_key: str,
    organization: str | None = None,
    project: str | None = None,
) -> PlatformStreamResponse:
    url = f"{base_url.rstrip('/')}/v1/responses"
    headers = build_platform_headers(
        api_key,
        organization=organization,
        project=project,
        accept="text/event-stream",
    )
    timeout = aiohttp.ClientTimeout(total=_RESPONSES_TIMEOUT_SECONDS)
    session = get_http_client().session
    response = await session.post(url, headers=headers, json=dict(payload), timeout=timeout)
    if response.status >= 400:
        try:
            body = await _read_response_body(response)
        finally:
            response.release()
        raise OpenAIPlatformError(
            response.status,
            _normalize_error_payload(body, response.status),
            upstream_request_id=response.headers.get("x-request-id"),
        )
    return PlatformStreamResponse(
        event_stream=_stream_response_events(response),
        upstream_request_id=response.headers.get("x-request-id"),
    )


async def _stream_response_events(response: aiohttp.ClientResponse) -> AsyncIterator[str]:
    try:
        async for event_block in _iter_sse_event_blocks(cast(_ChunkedResponse, response)):
            yield event_block
    finally:
        response.release()


def failed_event_payload(status_code: int, payload: dict[str, JsonValue]) -> str:
    error_payload = _normalize_error_payload(payload, status_code)
    return format_sse_event(error_payload)


def _normalize_error_payload(payload: JsonValue | None, status_code: int) -> dict[str, JsonValue]:
    if is_json_dict(payload):
        parsed_error = parse_error_payload(payload)
        if parsed_error is not None:
            return payload
    if is_json_dict(payload):
        return payload
    if isinstance(payload, str):
        message = payload.strip()
        if message:
            return cast("dict[str, JsonValue]", openai_error(f"platform_http_{status_code}", message))
    return _server_error(f"platform_http_{status_code}")


def _server_error(code: str) -> dict[str, JsonValue]:
    return cast("dict[str, JsonValue]", openai_error(code, "OpenAI Platform upstream error"))


async def _read_response_body(response: aiohttp.ClientResponse) -> JsonValue | None:
    try:
        return cast(JsonValue, await response.json(content_type=None))
    except (ValueError, UnicodeDecodeError):
        body = await response.read()
        if not body:
            return None
        return body.decode("utf-8", errors="replace")


def _find_sse_separator(buffer: bytes | bytearray) -> tuple[int, int] | None:
    separators = (b"\r\n\r\n", b"\n\n")
    positions = [(buffer.find(separator), len(separator)) for separator in separators]
    valid_positions = [position for position in positions if position[0] >= 0]
    if not valid_positions:
        return None
    return min(valid_positions, key=lambda item: item[0])


def _pop_sse_event(buffer: bytearray) -> bytes | None:
    separator = _find_sse_separator(buffer)
    if separator is None:
        return None
    index, separator_len = separator
    event_end = index + separator_len
    event = bytes(buffer[:event_end])
    del buffer[:event_end]
    return event


async def _iter_sse_event_blocks(response: _ChunkedResponse) -> AsyncIterator[str]:
    buffer = bytearray()
    async for chunk in response.content.iter_chunked(4096):
        if not chunk:
            continue
        buffer.extend(chunk)
        while True:
            raw_event = _pop_sse_event(buffer)
            if raw_event is None:
                break
            if raw_event.strip():
                yield raw_event.decode("utf-8", errors="replace")

    if buffer and buffer.strip():
        yield bytes(buffer).decode("utf-8", errors="replace")
