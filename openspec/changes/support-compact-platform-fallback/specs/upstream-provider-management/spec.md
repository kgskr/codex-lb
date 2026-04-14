## MODIFIED Requirements

### Requirement: Mixed-provider routing policy is explicit
The system MUST expose an explicit route-family eligibility policy for each upstream identity. In phase 1, `openai_platform` identities are fallback-only behind the existing ChatGPT pool, automatically enable the full supported enum of route families, and are not silently merged into unsupported ChatGPT-private behavior. When `public_responses_http` or `backend_codex_http` is enabled for `openai_platform`, that eligibility MUST cover both the standard stateless HTTP Responses route and the matching stateless HTTP compact route for that family, subject to provider capability and request-shape checks.

#### Scenario: Platform identity enables every supported route family by default
- **WHEN** an operator adds an `openai_platform` upstream identity
- **THEN** the router stores the full phase-1 supported route-family set for that identity
- **AND** the dashboard/API does not require the operator to opt into individual route families

#### Scenario: Platform identity remains eligible for the full supported route-family set on update
- **WHEN** an operator updates an existing `openai_platform` identity
- **THEN** the router keeps that identity eligible for the full supported route-family set
- **AND** it continues excluding the identity from unsupported websocket and continuity-dependent phase-1 behavior
- **AND** it MAY still consider that identity for a family's stateless compact HTTP route when the provider advertises compact support for that family

#### Scenario: Codex backend HTTP route family stays part of the supported Platform scope
- **WHEN** the system exposes the fixed supported route-family policy for `openai_platform`
- **THEN** the supported enum includes `backend_codex_http`
- **AND** a registered Platform identity is eligible for `backend_codex_http` alongside the other phase-1 supported route families

#### Scenario: Healthy ChatGPT-web pool stays primary for supported public routes
- **WHEN** a request targets an eligible public HTTP route
- **AND** both `chatgpt_web` and `openai_platform` identities are configured for that route family
- **AND** at least one compatible ChatGPT-web account remains selectable for the request
- **AND** that candidate remains above the configured primary and secondary drain thresholds
- **THEN** the service keeps routing through the ChatGPT-web pool
- **AND** it does not select the Platform identity for that request

#### Scenario: Platform becomes fallback when the compatible ChatGPT pool has no healthy candidates
- **WHEN** a request targets an eligible route family
- **AND** both `chatgpt_web` and `openai_platform` identities are configured in the deployment
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service MAY select the Platform identity as fallback for that request
- **AND** it does so only for `/v1/models`, stateless HTTP `/v1/responses`, stateless HTTP `/v1/responses/compact`, `/backend-api/codex/models`, stateless HTTP `/backend-api/codex/responses`, or stateless HTTP `/backend-api/codex/responses/compact`

#### Scenario: Blocked ChatGPT accounts do not suppress Platform fallback
- **WHEN** a request targets an eligible fallback route family
- **AND** every compatible ChatGPT-web account is currently unselectable because it is still rate-limited, quota-blocked, paused, or deactivated
- **THEN** the service MAY treat the ChatGPT pool as drained for Platform fallback
- **AND** persisted remaining percentages on those blocked accounts MUST NOT keep the request on ChatGPT by themselves

#### Scenario: Prompt-cache affinity does not override a drained public fallback decision
- **WHEN** a stateless public HTTP request carries a bounded `prompt_cache_key` affinity
- **AND** no compatible ChatGPT-web candidate remains selectable and above the configured fallback thresholds
- **THEN** the service MAY route the request to `openai_platform` fallback
- **AND** prompt-cache affinity alone MUST NOT suppress that provider fallback decision

#### Scenario: Healthy sticky Codex session may suppress fallback during grace
- **WHEN** a backend Codex HTTP request carries a durable `codex_session` affinity
- **AND** the pinned ChatGPT-web account is transiently rate-limited but becomes selectable within the sticky grace window
- **AND** that pinned account remains above the configured fallback thresholds at that grace-window selection point
- **THEN** the service keeps the request on ChatGPT-web for that session
- **AND** it does not switch that request to `openai_platform`

#### Scenario: Phase-1 route-family enum is fixed and testable
- **WHEN** the system exposes route-family eligibility controls for `openai_platform`
- **THEN** the supported phase-1 enum values are fixed and testable
- **AND** they include only `public_models_http`, `public_responses_http`, and `backend_codex_http`

### Requirement: Provider capabilities gate route eligibility
Each upstream identity MUST expose or derive a provider capability set that the router and balancer use before selection. The service MUST filter by provider capability before it chooses the concrete upstream identity for a request.

#### Scenario: Platform identity is excluded from unsupported ChatGPT-private route selection
- **WHEN** a request requires an unsupported ChatGPT-private capability such as backend Codex websocket transport
- **AND** the candidate upstream identity is `openai_platform`
- **THEN** the selection process excludes that identity before the normal routing strategy runs

#### Scenario: Eligible standard Responses route can fall back to Platform only after the compatible ChatGPT pool is drained
- **WHEN** a request targets an eligible route family such as stateless HTTP `/v1/responses` or stateless HTTP `/backend-api/codex/responses`
- **AND** both `chatgpt_web` and `openai_platform` identities advertise support for the request
- **AND** the Platform identity carries the fixed phase-1 supported route-family policy
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service may route the request to the Platform identity as fallback
- **AND** it MUST NOT treat Platform as an equal-weight member of the normal ChatGPT routing pool

#### Scenario: Eligible compact route can fall back to Platform only after the compatible ChatGPT pool is drained
- **WHEN** a request targets stateless HTTP `/v1/responses/compact` or stateless HTTP `/backend-api/codex/responses/compact`
- **AND** both `chatgpt_web` and `openai_platform` identities advertise compact support for the request
- **AND** the Platform identity carries the fixed phase-1 supported route-family policy
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service may route the compact request to the Platform identity as fallback
- **AND** it MUST keep the request inside the compact contract of the selected provider
