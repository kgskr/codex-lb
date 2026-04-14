## MODIFIED Requirements

### Requirement: Public OpenAI-compatible route eligibility is provider-aware, transport-aware, and fallback-ordered
The service MUST treat upstream execution as a provider-aware decision instead of assuming every request targets the ChatGPT-web backend. `chatgpt_web` remains primary and `openai_platform` is fallback-only. Phase-1 Platform fallback covers HTTP `/v1/models`, stateless HTTP `/v1/responses`, stateless HTTP `/v1/responses/compact`, HTTP `/backend-api/codex/models`, stateless HTTP `/backend-api/codex/responses`, and stateless HTTP `/backend-api/codex/responses/compact` when the selected routing subject supports the requested route family, transport, model, and required features.

#### Scenario: Healthy ChatGPT-web remains primary for stateless public HTTP
- **WHEN** a request targets an eligible public HTTP route
- **AND** both `chatgpt_web` and `openai_platform` are configured for that route family
- **AND** at least one compatible ChatGPT-web candidate remains healthy under the configured primary and secondary drain thresholds
- **THEN** the request continues through the ChatGPT-web path
- **AND** the service does not switch to the Platform transport for that request

#### Scenario: HTTP `/v1/responses` falls back to an OpenAI Platform upstream after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available for the requested model
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured primary and secondary drain thresholds
- **AND** the request does not require phase-1 unsupported continuity or websocket capabilities
- **THEN** the service forwards HTTP `/v1/responses` to the public upstream contract instead of the ChatGPT-private `/codex/responses` path

#### Scenario: HTTP `/v1/responses/compact` falls back to an OpenAI Platform compact upstream after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available for the requested compact model
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service forwards HTTP `/v1/responses/compact` through the Platform compact transport
- **AND** it does not rewrite the compact result into a normal Responses payload

#### Scenario: Backend Codex HTTP responses fall back to Platform after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available for the requested model
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **AND** the request does not require websocket or payload-level continuity-dependent behavior
- **THEN** the service forwards HTTP `/backend-api/codex/responses` through the Platform transport instead of the ChatGPT-private upstream path

#### Scenario: Backend Codex HTTP compact responses fall back to Platform after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available for the requested compact model
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service forwards HTTP `/backend-api/codex/responses/compact` through the Platform compact transport
- **AND** it preserves the compact result as the canonical next context window

#### Scenario: Backend Codex HTTP model discovery falls back to Platform after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service may satisfy HTTP `/backend-api/codex/models` from Platform model discovery translated into the backend Codex response shape

#### Scenario: Platform identity is excluded from downstream websocket route selection in phase 1
- **WHEN** a request targets downstream websocket `/responses` or `/v1/responses`
- **AND** the candidate upstream routing subject is `openai_platform`
- **THEN** the service excludes that routing subject before transport start
- **AND** if no compatible `chatgpt_web` routing subject remains it returns a stable OpenAI-format error instead of attempting a ChatGPT-shaped websocket flow on behalf of Platform mode

#### Scenario: capability mismatch fails closed
- **WHEN** routing selects or is restricted to an upstream routing subject that does not support the requested route family, transport, or feature
- **THEN** the service rejects the request with a stable OpenAI-format error
- **AND** it MUST NOT silently substitute a different upstream contract to emulate unsupported behavior

#### Scenario: Public route rejects Platform-only fallback
- **WHEN** a request targets HTTP `/v1/models`, stateless HTTP `/v1/responses`, or stateless HTTP `/v1/responses/compact`
- **AND** an `openai_platform` identity is configured for that route family
- **AND** no eligible `chatgpt_web` routing subject exists for the requested model and route
- **THEN** the service rejects the request before upstream transport start with HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `type = "invalid_request_error"` and `code = "provider_fallback_requires_chatgpt"`

### Requirement: Compact requests preserve upstream compaction semantics
To preserve provider-owned remote compaction semantics, the service MUST fulfill `/backend-api/codex/responses/compact` and `/v1/responses/compact` by calling the selected provider's native compact endpoint directly and returning the upstream JSON payload as the canonical next context window without converting it into a standard buffered Responses result. The service MUST preserve provider-owned compact payload contents without pruning, reordering, or rewriting returned context items beyond generic JSON serialization. While using this direct compact transport, the service MUST preserve compact account-selection semantics, `session_id` affinity, `prompt_cache_key` affinity, provider-aware request logging, API key settlement, and bounded same-contract retries. The service MUST reject `store=true` as a client payload error, and it MUST omit `store` from the direct upstream compact request instead of forwarding `store=false`. If direct upstream compact execution fails before a valid compact JSON payload is accepted, the service MUST keep the request inside the compact contract of the selected provider. It MUST NOT silently substitute a standard `/responses` request, reconstruct compact output from streamed Responses events, or synthesize a compact window locally. The service MAY perform provider-specific transport timeouts and a bounded retry only against the selected provider's compact endpoint when the failure occurs in a provably safe transport phase before a valid compact JSON payload is accepted.

#### Scenario: Compact request returns raw upstream compaction payload
- **WHEN** a compact request succeeds and the selected provider's compact endpoint returns `object: "response.compaction"`
- **THEN** the service returns that JSON payload without rewriting it into `object: "response"`

#### Scenario: Compact request preserves provider-owned compaction summary
- **WHEN** the upstream compact response includes nested compaction fields such as `compaction_summary.encrypted_content`
- **THEN** the service returns those nested fields unchanged in the final JSON response

#### Scenario: Compact response includes retained items and encrypted compaction state
- **WHEN** the upstream compact response returns a window that includes retained context items plus provider-owned compaction state such as encrypted content
- **THEN** the service returns that window unchanged to the client

#### Scenario: Compact response object shape differs from normal Responses
- **WHEN** the upstream compact response uses a provider-owned compact object shape instead of a standard `object: "response"` payload
- **THEN** the service returns that compact object shape unchanged instead of coercing it into a normal Responses payload

#### Scenario: Direct compact request omits store
- **WHEN** a client sends `/backend-api/codex/responses/compact` or `/v1/responses/compact` without a `store` field
- **THEN** the selected provider-native compact request omits `store`

#### Scenario: Direct compact request sets store true
- **WHEN** a client sends `/backend-api/codex/responses/compact` or `/v1/responses/compact` with `store=true`
- **THEN** the service returns a 4xx OpenAI invalid payload error
- **AND** it does not forward any `store` field upstream

#### Scenario: Direct compact upstream returns an error envelope
- **WHEN** the selected provider-native compact request returns a non-2xx OpenAI-format error payload
- **THEN** the service propagates the corresponding HTTP status and error envelope to the client

#### Scenario: Backend Codex compact falls back to public Platform compact transport
- **WHEN** a client sends `/backend-api/codex/responses/compact`
- **AND** the selected upstream routing subject is `openai_platform`
- **THEN** the service translates the request onto the public Platform compact contract
- **AND** it still returns the resulting compact payload unchanged to the backend Codex client

#### Scenario: Grace-eligible backend Codex session stays on ChatGPT compact
- **WHEN** `/backend-api/codex/responses/compact` carries a durable `session_id` affinity
- **AND** the pinned ChatGPT-web account is transiently rate-limited but becomes selectable within the sticky grace window
- **AND** the pinned account remains above the configured fallback thresholds at that grace-window selection point
- **THEN** the service keeps the compact request on the ChatGPT compact transport
- **AND** it does not route that request to Platform fallback

#### Scenario: Public compact prompt-cache affinity does not suppress provider fallback
- **WHEN** `/v1/responses/compact` carries a bounded `prompt_cache_key` affinity
- **AND** no compatible ChatGPT-web candidate remains selectable and above the configured fallback thresholds
- **THEN** the service MAY route the request to the Platform compact transport
- **AND** prompt-cache affinity alone MUST NOT keep the request on ChatGPT

#### Scenario: Direct compact transport fails before response body is available
- **WHEN** the selected provider's compact call times out, disconnects, or otherwise fails before yielding a valid compact JSON payload
- **THEN** the service may retry only that provider's compact endpoint within a bounded retry budget
- **AND** it does not attempt a surrogate standard `/responses` request

#### Scenario: Direct compact transport gets a safe retryable upstream failure
- **WHEN** the selected provider's compact call fails with `401`, `502`, `503`, or `504` before a valid compact JSON payload is accepted
- **THEN** the service may retry only that provider's compact endpoint
- **AND** it preserves the request's established compact routing and affinity semantics except for refreshed provider identity on `401`
- **AND** it does not call a standard `/responses` endpoint

#### Scenario: Direct compact response payload is invalid
- **WHEN** the selected provider's compact call returns a non-error payload that is not valid compact JSON for pass-through
- **THEN** the service returns an upstream error to the client
- **AND** it does not retry via a standard `/responses` endpoint
- **AND** it does not synthesize or reconstruct a replacement compact window

#### Scenario: ChatGPT compact request uses no timeout by default
- **WHEN** `/responses/compact` is routed to the `chatgpt_web` compact endpoint
- **AND** no compact timeout override is configured
- **THEN** the service forwards the request without setting an upstream total or read timeout
