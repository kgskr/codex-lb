# Upstream Provider Management Context

## Purpose and Scope

This capability defines how the dashboard and API manage provider-aware upstream identities, including ChatGPT-web accounts and the phase-1 OpenAI Platform fallback identity.

See `openspec/specs/upstream-provider-management/spec.md` for normative requirements.

## Decisions

- `chatgpt_web` remains the primary upstream for existing behavior.
- `openai_platform` is fallback-only in phase 1 and is intentionally narrow in scope.
- Phase 1 mixed-provider mode supports only one Platform API key.
- Provider-aware routing is explicit rather than treating Platform as an equal-weight member of the ChatGPT pool.

## Supported Fallback Routes

- `GET /v1/models`
- stateless HTTP `POST /v1/responses`
- stateless HTTP `POST /v1/responses/compact`
- `GET /backend-api/codex/models`
- stateless HTTP `POST /backend-api/codex/responses`
- stateless HTTP `POST /backend-api/codex/responses/compact`

For backend Codex HTTP responses, downstream Codex session headers such as `session_id`, `x-codex-session-id`, `x-codex-conversation-id`, and `x-codex-turn-state` are treated as transport hints in phase 1. They do not, by themselves, suppress an otherwise eligible Platform fallback decision. A durable `codex_session` mapping may still keep a request on ChatGPT when its pinned ChatGPT target becomes selectable within the sticky grace window and still satisfies the fallback thresholds at that selection point, but that session affinity does not create a durable Platform-side session pin in phase 1.

## Unsupported Platform-backed Routes in Phase 1

- downstream websocket `/responses`
- downstream websocket `/v1/responses`
- downstream websocket `/backend-api/codex/responses`
- `/v1/chat/completions`
- continuity-dependent requests using `conversation` or `previous_response_id`

## Fallback Policy

- ChatGPT accounts remain primary whenever at least one compatible `chatgpt_web` candidate has both `primary_remaining_percent > 10` and `secondary_remaining_percent > 5`.
- Platform fallback is allowed only when every compatible ChatGPT candidate is outside that healthy window.
- Candidates that are still rate-limited, quota-blocked, paused, or deactivated do not suppress Platform fallback based on persisted remaining percentages alone.
- `prompt_cache_key` affinity preserves cache locality within a provider but does not, by itself, override a drained public-route fallback decision.
- Credits are not part of the fallback decision.

## Operational Constraints

- Platform fallback requires at least one active ChatGPT account.
- A Platform identity is registered with the full supported route-family set and does not expose per-route opt-in in phase 1.
- Repeated upstream `401` or `403` failures should deactivate the Platform identity until the operator repairs or re-enables it.

## UX Expectations

- The dashboard should describe Platform identities as fallback-only.
- Route-family labels should clarify that `public_responses_http` covers stateless HTTP `/v1/responses` plus `/v1/responses/compact`.
- Route-family labels should clarify that `backend_codex_http` covers `/backend-api/codex/models`, stateless HTTP `/backend-api/codex/responses`, and `/backend-api/codex/responses/compact`.
- Operators should not expect websocket or continuity-dependent behavior from the Platform path in phase 1.
