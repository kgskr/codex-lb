from __future__ import annotations

import pytest

from app.core.clients import proxy as proxy_client

pytestmark = pytest.mark.unit


def test_resolve_codex_models_client_version_prefers_explicit_header() -> None:
    version = proxy_client._resolve_codex_models_client_version(
        {
            "x-openai-client-version": "0.120.0",
            "user-agent": "Codex Desktop/0.119.0",
        }
    )

    assert version == "0.120.0"


def test_resolve_codex_models_client_version_extracts_semver_from_user_agent() -> None:
    version = proxy_client._resolve_codex_models_client_version(
        {
            "user-agent": "Codex Desktop/0.120.0 (darwin; arm64)",
        }
    )

    assert version == "0.120.0"
