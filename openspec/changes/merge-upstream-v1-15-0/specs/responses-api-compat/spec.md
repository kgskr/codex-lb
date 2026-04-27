## MODIFIED Requirements

### Requirement: Allow web_search tools and reject unsupported built-ins
The service MUST accept Responses requests that include tools with type `web_search` or `web_search_preview` and MUST normalize `web_search_preview` to `web_search` before forwarding upstream. For other built-in Responses tool types (including `file_search`, `code_interpreter`, `computer_use`, `computer_use_preview`, and `image_generation`), the service MUST accept the request and MUST forward the tool definitions to upstream unchanged except for the documented `web_search_preview` alias. The same behavior MUST apply on HTTP `/v1/responses`, HTTP `/backend-api/codex/responses`, and the WebSocket equivalents that carry `response.create` payloads. Chat Completions tool policy is out of scope for this requirement and remains governed by `chat-completions-compat`.

#### Scenario: web_search_preview tool accepted
- **WHEN** the client sends `tools=[{"type":"web_search_preview"}]`
- **THEN** the service accepts the request and forwards the tool as `web_search`

#### Scenario: built-in Responses tool accepted over HTTP
- **WHEN** the client sends `/v1/responses` or `/backend-api/codex/responses` with a built-in tool such as `image_generation`, `file_search`, `code_interpreter`, `computer_use`, or `computer_use_preview`
- **THEN** the service accepts the request and forwards the tool definition unchanged except for the documented `web_search_preview` alias

#### Scenario: built-in Responses tool accepted over WebSocket
- **WHEN** the client sends a WebSocket `response.create` payload on `/v1/responses` or `/backend-api/codex/responses` with one or more built-in tools
- **THEN** the service accepts the request and forwards the tool definitions unchanged except for the documented `web_search_preview` alias

## ADDED Requirements

### Requirement: Continuity recovery reuses session-level response state after reconnect-only failures

For bridged HTTP Responses sessions, the service MUST persist session-level latest-response state and use it during reconnect-only recovery so retried requests can restore or inject `previous_response_id` instead of replaying the full accumulated prompt.

#### Scenario: Reconnect-only recovery injects previous response state
- **WHEN** a bridged HTTP Responses request is retried after reconnect-only recovery and the session already has a completed upstream response id
- **THEN** the retry forwards that response id upstream
- **AND** it trims replayed input to the new incremental turn instead of resending the full prior transcript

#### Scenario: Missing recovery state fails closed
- **WHEN** a retry requires bridged continuity but the session lacks usable prior response state
- **THEN** the service rejects the request with a continuity error
- **AND** it does not fall back to replaying an oversized full-context request

### Requirement: Responses routes recognize upstream `v1.15.0` GPT-5.5 model identifiers

The merged routing layer MUST accept upstream `gpt-5.5` and `gpt-5.5-pro` model identifiers on supported Responses-family routes and MUST not reject those models locally solely because local metadata predates `v1.15.0`.

#### Scenario: GPT-5.5 models are accepted on supported Responses routes
- **WHEN** a client sends a supported Responses-family request for `gpt-5.5` or `gpt-5.5-pro`
- **THEN** the service keeps the request on a supported upstream route
- **AND** it returns the normal success or upstream-model error contract instead of rejecting the model locally

#### Scenario: Backend Codex model discovery reflects the current client version on ChatGPT-primary routes
- **WHEN** a client requests HTTP `/backend-api/codex/models`
- **AND** the request identifies a newer Codex client version through `x-openai-client-version` or the native Codex user agent
- **AND** `chatgpt_web` remains the selected primary provider for backend Codex HTTP
- **THEN** the service performs live upstream ChatGPT model discovery using that client version instead of relying only on the cached local registry snapshot
- **AND** GPT-5.5 entries returned by upstream remain visible in the backend Codex model list response

### Requirement: Platform-routed Responses requests downgrade the `fast` tier alias to `default`

When a Responses-family request is routed through `openai_platform`, the service MUST continue to normalize the client-visible `fast` alias to canonical `priority` for validation, diagnostics, and requested-tier logging. If the original client-supplied tier was `fast`, the service MUST forward `service_tier: "default"` to the Platform upstream and MUST use that forwarded default tier as the fallback effective tier when the upstream response omits a `service_tier` echo.

#### Scenario: Stateless platform fallback sends default tier upstream for fast alias
- **WHEN** a client sends an eligible HTTP `/v1/responses` or `/backend-api/codex/responses` request with `service_tier: "fast"`
- **AND** provider selection routes the request through `openai_platform`
- **THEN** the upstream Platform payload includes `service_tier: "default"`
- **AND** request logs keep `requested_service_tier: "priority"`

#### Scenario: Platform response omits service_tier after fast alias fallback
- **WHEN** the original client-supplied tier was `fast`
- **AND** the Platform upstream response completes without a `service_tier` field
- **THEN** the service records `service_tier: "default"` as the effective tier
- **AND** it does not fall back to `priority` pricing or logging for that request
