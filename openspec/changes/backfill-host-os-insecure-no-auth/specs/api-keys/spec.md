## MODIFIED Requirements

### Requirement: API Key Bearer authentication guard

The system SHALL validate API keys on proxy routes (`/v1/*`, `/backend-api/codex/*`, `/backend-api/transcribe`) when `api_key_auth_enabled` is true.

When `insecure_allow_remote_no_auth=true` and the request is positively identified as originating from the host OS network, the dependency MAY bypass Bearer validation and return `None` even when `api_key_auth_enabled=true`. Host-header spoofing alone MUST NOT qualify a request for this bypass.

#### Scenario: Host-OS request bypasses API key validation

- **WHEN** `api_key_auth_enabled` is true
- **AND** `insecure_allow_remote_no_auth=true`
- **AND** the request is classified as a host-OS request
- **THEN** the API-key guard returns `None`
- **AND** the request proceeds without Bearer validation

#### Scenario: Public remote request still requires an API key

- **WHEN** `api_key_auth_enabled` is true
- **AND** `insecure_allow_remote_no_auth=true`
- **AND** the request is not classified as a host-OS request
- **THEN** the API-key guard still requires a valid Bearer API key
