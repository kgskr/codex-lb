# upstream-provider-management Specification

## Purpose

Define provider-aware upstream identity management, credential lifecycle rules, and mixed-provider routing eligibility.

## Requirements
### Requirement: Dashboard manages provider-specific upstream identities
The system SHALL allow operators to manage upstream identities for at least two provider kinds: `chatgpt_web` and `openai_platform`. Each identity MUST declare its provider kind explicitly, and the dashboard MUST present provider-specific create and edit flows instead of forcing all upstream credentials through the ChatGPT OAuth path.

#### Scenario: Operator creates an OpenAI Platform upstream identity
- **WHEN** the operator creates an `openai_platform` upstream identity
- **THEN** the dashboard collects a human label, encrypted API key material, and optional organization or project metadata
- **AND** the system automatically applies the fixed phase-1 supported route-family set for that identity
- **AND** the system stores that identity without requiring ChatGPT OAuth tokens, `refresh_token`, `id_token`, or `chatgpt_account_id`

#### Scenario: Platform identity requires an existing ChatGPT-web pool
- **WHEN** the operator attempts to create an `openai_platform` upstream identity
- **AND** there is no active `chatgpt_web` account available to serve the existing primary path
- **THEN** the system rejects the create request
- **AND** it explains that Platform fallback requires at least one active ChatGPT-web account

#### Scenario: Only one Platform identity may exist
- **WHEN** the operator attempts to create a second `openai_platform` upstream identity
- **THEN** the system rejects the create request
- **AND** it explains that phase-1 mixed-provider mode supports only one Platform API key

#### Scenario: Operator creates a ChatGPT-web upstream identity
- **WHEN** the operator creates a `chatgpt_web` upstream identity
- **THEN** the existing OAuth or `auth.json`-import flow remains available
- **AND** the system continues storing the ChatGPT-specific credential set required for that provider

### Requirement: Platform identities use split persistence, not fake ChatGPT account fields
The system MUST store `openai_platform` credentials in a provider-appropriate persistence model and MUST NOT require fake ChatGPT account fields such as refresh tokens, `id_token`, or `chatgpt_account_id` to represent a valid Platform identity.

#### Scenario: Platform identity persists without ChatGPT account fields
- **WHEN** the system persists an `openai_platform` upstream identity
- **THEN** it stores provider-appropriate credential and metadata fields only
- **AND** it does not depend on nullable fake ChatGPT lifecycle fields to keep the record valid

### Requirement: Provider credentials follow provider-specific lifecycle rules
The system MUST apply credential lifecycle behavior according to provider kind. `chatgpt_web` identities continue to use token refresh and account-claim extraction. `openai_platform` identities MUST NOT enter the ChatGPT OAuth refresh lifecycle and MUST instead use provider-appropriate key validation and health transitions.

#### Scenario: Platform upstream request uses bearer auth and optional org/project headers
- **WHEN** the system sends an upstream request through an `openai_platform` identity
- **THEN** it sends `Authorization: Bearer <api_key>`
- **AND** it sends `OpenAI-Organization` only when the identity configures organization metadata
- **AND** it sends `OpenAI-Project` only when the identity configures project metadata

#### Scenario: Platform upstream identity validates without refresh tokens
- **WHEN** the system validates an `openai_platform` upstream identity
- **THEN** it performs API-key validation with `GET /v1/models` using the same auth headers as normal Platform requests
- **AND** a `2xx` response marks validation success
- **AND** repeated `401` or `403` responses are treated as credential failure
- **AND** it MUST NOT attempt to call the ChatGPT OAuth refresh path for that identity

#### Scenario: Platform upstream identity fails closed after repeated upstream auth failures
- **WHEN** an `openai_platform` upstream identity repeatedly receives upstream `401` or `403` authentication failures
- **THEN** the system marks that identity unhealthy or deactivated according to provider-specific policy
- **AND** it stops selecting that identity for new requests until the operator repairs or re-enables it

### Requirement: Mixed-provider routing policy is explicit
The system MUST expose an explicit route-family eligibility policy for each upstream identity. In phase 1, `openai_platform` identities are fallback-only behind the existing ChatGPT pool, automatically enable the full supported route-family set, and are not silently merged into unsupported ChatGPT-private behavior.

#### Scenario: Platform identity enables every supported route family by default
- **WHEN** an operator adds an `openai_platform` upstream identity
- **THEN** the router stores the full supported phase-1 route-family set for that identity
- **AND** the dashboard/API does not require the operator to opt into individual route families

#### Scenario: Platform identity remains eligible for the full supported route-family set on update
- **WHEN** an operator updates an existing `openai_platform` identity
- **THEN** the router keeps that identity eligible for the full supported route-family set
- **AND** it continues excluding the identity from unsupported websocket and continuity-dependent phase-1 behavior

#### Scenario: Codex backend HTTP route family stays part of the supported Platform scope
- **WHEN** the system exposes the supported route-family policy for `openai_platform`
- **THEN** the supported enum includes `backend_codex_http`
- **AND** a registered Platform identity stays eligible for `backend_codex_http` alongside the other supported route families

#### Scenario: Healthy ChatGPT-web pool stays primary for supported public routes
- **WHEN** a request targets an eligible public HTTP route
- **AND** both `chatgpt_web` and `openai_platform` identities are configured for that route family
- **AND** at least one compatible ChatGPT-web account remains healthy under the configured primary and secondary drain thresholds
- **THEN** the service keeps routing through the ChatGPT-web pool
- **AND** it does not select the Platform identity for that request

#### Scenario: Platform becomes fallback when the compatible ChatGPT pool has no healthy candidates
- **WHEN** a request targets an eligible route family
- **AND** both `chatgpt_web` and `openai_platform` identities are configured for that route family
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service MAY select the Platform identity as fallback for that request
- **AND** it does so only for `/v1/models`, stateless HTTP `/v1/responses`, stateless HTTP `/v1/responses/compact`, `/backend-api/codex/models`, stateless HTTP `/backend-api/codex/responses`, or stateless HTTP `/backend-api/codex/responses/compact`

#### Scenario: Phase-1 route-family enum is fixed and testable
- **WHEN** the system exposes route-family eligibility controls for `openai_platform`
- **THEN** the supported phase-1 enum values are fixed and testable
- **AND** they include only `public_models_http`, `public_responses_http`, and `backend_codex_http`

### Requirement: Platform fallback uses the remaining percentages visible to operators

For phase-1 fallback, the service MUST treat a compatible ChatGPT-web candidate as healthy only while it remains selectable for the request and both persisted usage snapshots required for fallback evaluation are present with `primary_remaining_percent > 10` and `secondary_remaining_percent > 5`. Compatible candidates with either snapshot missing MUST NOT count as healthy for suppressing Platform fallback. Candidates that are still rate-limited, quota-blocked, paused, or deactivated MUST NOT suppress Platform fallback based on persisted remaining percentages alone. A durable backend Codex `codex_session` affinity MAY still suppress Platform fallback for its pinned ChatGPT-web account when that pinned target becomes selectable within the sticky grace window and remains above the same remaining-percent thresholds at that grace-window selection point. When no compatible ChatGPT-web candidate remains positively healthy under those thresholds, the service MAY consider `openai_platform` as fallback, subject to the existing route-family eligibility checks.

#### Scenario: A compatible ChatGPT-web candidate with more than 10 percent primary remaining and more than 5 percent secondary remaining keeps Platform idle

- **WHEN** a request targets an eligible Platform fallback route family
- **AND** both `chatgpt_web` and `openai_platform` are configured for that route family
- **AND** at least one compatible ChatGPT-web candidate has both `primary_remaining_percent > 10` and `secondary_remaining_percent > 5`
- **THEN** the service keeps routing through the ChatGPT-web pool

#### Scenario: Platform fallback may activate once no compatible candidate remains healthy under the remaining-percent thresholds

- **WHEN** a request targets an eligible Platform fallback route family
- **AND** both `chatgpt_web` and `openai_platform` are configured for that route family
- **AND** each compatible ChatGPT-web candidate has `primary_remaining_percent <= 10` or `secondary_remaining_percent <= 5`
- **THEN** the service MAY select the Platform identity as fallback for that request

#### Scenario: Blocked candidates do not suppress Platform fallback
- **WHEN** a request targets an eligible Platform fallback route family
- **AND** every compatible ChatGPT-web candidate is currently unselectable because it is still rate-limited, quota-blocked, paused, or deactivated
- **THEN** the service MAY treat the ChatGPT pool as drained for Platform fallback
- **AND** persisted remaining percentages on those blocked candidates MUST NOT keep the request on ChatGPT by themselves

#### Scenario: Missing usage snapshots do not suppress Platform fallback

- **WHEN** a request targets an eligible Platform fallback route family
- **AND** both `chatgpt_web` and `openai_platform` are configured for that route family
- **AND** every compatible ChatGPT-web candidate with known persisted usage is outside the configured fallback thresholds
- **AND** another compatible ChatGPT-web candidate is missing either the primary or secondary persisted usage snapshot required for fallback evaluation
- **THEN** the missing usage snapshot MUST NOT keep the request on the ChatGPT path
- **AND** the service MAY select the Platform identity as fallback for that request

### Requirement: Provider capabilities gate route eligibility
Each upstream identity MUST expose or derive a provider capability set that the router and balancer use before selection. The service MUST filter by provider capability before it chooses the concrete upstream identity for a request.

#### Scenario: Platform identity is excluded from ChatGPT-private route selection
- **WHEN** a request requires an unsupported ChatGPT-private capability such as backend Codex websocket transport
- **AND** the candidate upstream identity is `openai_platform`
- **THEN** the selection process excludes that identity before the normal routing strategy runs

#### Scenario: Eligible route family can fall back to Platform only after the compatible ChatGPT pool is drained
- **WHEN** a request targets an eligible route family such as stateless HTTP `/v1/responses`, stateless HTTP `/v1/responses/compact`, stateless HTTP `/backend-api/codex/responses`, or stateless HTTP `/backend-api/codex/responses/compact`
- **AND** both `chatgpt_web` and `openai_platform` identities advertise support for the request
- **AND** the Platform identity carries the fixed supported route-family policy
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service may route the request to the Platform identity as fallback
- **AND** it MUST NOT treat Platform as an equal-weight member of the normal ChatGPT routing pool

### Requirement: Provider list and detail surfaces expose operational state
The system MUST expose provider-aware list/detail fields so operators can understand why an upstream identity is or is not eligible for a request.

#### Scenario: Provider summary includes route eligibility and health
- **WHEN** the dashboard or API returns a list of upstream identities
- **THEN** each item includes `provider_kind`, `routing_subject_id`, operator-visible label, health/status, eligible route families, and last validation timestamp

#### Scenario: Provider detail includes recent auth failure reason
- **WHEN** the dashboard or API returns a detail view for an upstream identity
- **THEN** the response includes the most recent provider-auth failure code or reason when available
- **AND** it includes configured organization and project metadata when present
