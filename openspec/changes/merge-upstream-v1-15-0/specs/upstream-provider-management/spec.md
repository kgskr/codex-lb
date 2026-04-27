## ADDED Requirements

### Requirement: Quota and deactivation state survive resets and restarts safely

The merged provider-management flow MUST preserve upstream account blocking semantics so quota-exceeded accounts recover only when the appropriate reset condition occurs, while deactivated accounts fail closed and remain unavailable across process restarts until explicitly repaired.

#### Scenario: Quota-blocked account recovers after the next valid reset window
- **WHEN** an account was blocked because of an upstream quota-exceeded condition before a restart or early reset boundary
- **THEN** the merged runtime keeps that account unavailable until the next valid recovery condition is reached
- **AND** the account becomes selectable again only after recovery is confirmed

#### Scenario: Deactivated account stays fail-closed
- **WHEN** upstream returns an account-deactivated condition for a routing subject
- **THEN** the merged runtime marks that subject unavailable
- **AND** it does not continue routing new requests to that subject until an operator repair or explicit revalidation succeeds

### Requirement: Provider model catalog includes upstream `v1.15.0` models

The merged provider model catalog MUST include the upstream `gpt-5.5` and `gpt-5.5-pro` identifiers with the routing and pricing metadata required for eligibility checks, API key filtering, and request handling.

#### Scenario: Model catalog exposes GPT-5.5 entries
- **WHEN** the merged runtime evaluates the provider model catalog
- **THEN** `gpt-5.5` and `gpt-5.5-pro` are present with the metadata required for routing and pricing

#### Scenario: API key and routing checks recognize GPT-5.5 models
- **WHEN** an authenticated request targets `gpt-5.5` or `gpt-5.5-pro`
- **THEN** model-allowlist checks and upstream selection use the merged catalog entries
- **AND** they do not fail because the models are missing from local metadata
