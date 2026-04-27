## MODIFIED Requirements

### Requirement: Password setup

The system SHALL allow the admin to set a password from the settings page when no password is currently configured. The password MUST be hashed with bcrypt before storage. Setting a password SHALL transition the system from unauthenticated mode to password-protected mode. When the request is positively identified as originating from the host OS network, first-time setup MAY proceed without a bootstrap token. When the request is non-local, first-time setup MUST require a valid `bootstrapToken` before the password is stored.

#### Scenario: First-time local password setup

- **WHEN** no password is configured (`password_hash` is NULL)
- **AND** the password setup request comes from a local or host-OS client
- **AND** admin submits `POST /api/dashboard-auth/password/setup` with `{ "password": "..." }`
- **THEN** the system stores a bcrypt hash in `DashboardSettings.password_hash`
- **AND** returns a session cookie with `pw=true`

#### Scenario: First-time remote password setup with bootstrap token

- **WHEN** no password is configured (`password_hash` is NULL)
- **AND** the password setup request comes from a non-local client
- **AND** admin submits `POST /api/dashboard-auth/password/setup` with `{ "password": "...", "bootstrapToken": "<valid token>" }`
- **THEN** the system stores a bcrypt hash in `DashboardSettings.password_hash`
- **AND** returns a session cookie with `pw=true`

#### Scenario: First-time remote password setup rejected without valid bootstrap token

- **WHEN** no password is configured (`password_hash` is NULL)
- **AND** the password setup request comes from a non-local client
- **AND** admin submits `POST /api/dashboard-auth/password/setup` without a valid `bootstrapToken`
- **THEN** the system rejects the request with a bootstrap-related authentication error
- **AND** it does not store the password hash

#### Scenario: Password setup rejected when already configured

- **WHEN** a password is already configured and admin submits `POST /api/dashboard-auth/password/setup`
- **THEN** the system returns 409 Conflict

#### Scenario: Password setup with weak password

- **WHEN** admin submits a password shorter than 8 characters
- **THEN** the system returns 422 with a validation error

### Requirement: Session authentication guard

The system SHALL enforce session authentication on `/api/*` routes except `/api/dashboard-auth/*`. Authentication SHALL be enforced via a router-level dependency guard, not ASGI middleware.

Authentication required condition: the system SHALL evaluate `password_hash` and `totp_required_on_login` together to determine whether authentication is required. When `password_hash` is NULL **and** `totp_required_on_login` is false, the guard MUST allow all requests (unauthenticated mode). When either `password_hash` is set **or** `totp_required_on_login` is true, the guard MUST require a valid session.

When `insecure_allow_remote_no_auth=true` and the request is positively identified as originating from the host OS network, the guard MAY bypass session enforcement for non-`/api/dashboard-auth/*` routes only while dashboard auth is otherwise disabled. Host-header spoofing alone MUST NOT qualify a request for this bypass.

Session validation steps when `requires_auth` is true:
1. A valid session cookie MUST be present (otherwise 401)
2. If `password_hash` is not NULL, the session MUST have `password_verified=true`
3. If `totp_required_on_login` is true, the session MUST have `totp_verified=true`

Migration inconsistency (`password_hash=NULL` with `totp_required_on_login=true`) SHALL always be treated as fail-closed — the system MUST NOT fall back to unauthenticated mode. The system SHOULD emit a warning log/metric for this inconsistency state.

The guard SHALL raise a domain exception on authentication failure. The exception handler SHALL format the response using the dashboard error envelope.

`GET /api/codex/usage` is an exception path for dashboard session auth: the system SHALL require a dedicated caller-identity dependency instead of the dashboard session guard. When the request includes `chatgpt-account-id`, the system SHALL validate the provided bearer token against that active ChatGPT account. When the request omits `chatgpt-account-id`, the same endpoint MAY satisfy caller identity with a valid codex-lb API key. A valid dashboard session cookie alone MUST NOT satisfy this path.

#### Scenario: Codex usage caller identity validation in password mode

- **WHEN** `password_hash` is set and `GET /api/codex/usage` is requested
- **AND** `Authorization` bearer token and `chatgpt-account-id` are provided
- **AND** `chatgpt-account-id` exists in LB accounts
- **AND** upstream usage validation succeeds for the token/account pair
- **THEN** the guard allows the request

#### Scenario: Codex usage caller identity required even with dashboard session

- **WHEN** `password_hash` is set and `GET /api/codex/usage` is requested with a valid dashboard session cookie
- **AND** codex bearer caller identity is missing
- **THEN** the guard returns 401

#### Scenario: Codex usage accepts valid API key without chatgpt-account-id

- **WHEN** `GET /api/codex/usage` is requested
- **AND** `Authorization` contains a valid codex-lb API key
- **AND** `chatgpt-account-id` is absent
- **THEN** the dedicated caller-identity dependency accepts the request
- **AND** the dashboard session guard does not run for that path

#### Scenario: Codex usage denied when caller identity is not authorized

- **WHEN** `GET /api/codex/usage` is requested
- **AND** codex bearer caller identity is missing or invalid
- **THEN** the guard returns 401

#### Scenario: Legacy TOTP protection preserved when password_hash is NULL

- **WHEN** `password_hash` is NULL and `totp_required_on_login` is true
- **AND** no session cookie is present
- **THEN** the guard returns 401

#### Scenario: TOTP-only session accepted when password is not configured

- **WHEN** `password_hash` is NULL and `totp_required_on_login` is true
- **AND** session has `password_verified=false` and `totp_verified=true`
- **THEN** the guard allows the request

#### Scenario: TOTP verification required even with password session

- **WHEN** `password_hash` is NULL and `totp_required_on_login` is true
- **AND** session has `password_verified=true` but `totp_verified=false`
- **THEN** the guard returns 401 with `totp_required` indication

#### Scenario: Host-OS request bypasses dashboard guard when auth is disabled

- **WHEN** `password_hash` is NULL and `totp_required_on_login` is false
- **AND** `insecure_allow_remote_no_auth=true`
- **AND** the request is classified as a host-OS request
- **THEN** non-`/api/dashboard-auth/*` dashboard routes bypass session auth

#### Scenario: Spoofed localhost host header does not bypass dashboard guard

- **WHEN** `insecure_allow_remote_no_auth=true`
- **AND** a remote public client sends `Host: localhost`
- **AND** the request does not otherwise prove host-network origin
- **THEN** the dashboard guard does not bypass authentication or remote bootstrap checks

#### Scenario: Host-OS bypass stops once password or TOTP auth is required

- **WHEN** `insecure_allow_remote_no_auth=true`
- **AND** the request is classified as a host-OS request
- **AND** `password_hash` is set or `totp_required_on_login` is true
- **THEN** the dashboard guard requires a valid session

## ADDED Requirements

### Requirement: Bootstrap token lifecycle is visible to operators

When dashboard auth is unconfigured and remote bootstrap is possible, the system MUST maintain a persisted bootstrap-token lifecycle that operators can recover and clients can reason about. The session endpoint MUST expose whether remote bootstrap is required and whether a bootstrap token is currently configured for non-local setup. When the runtime auto-generates the initial bootstrap token, it MUST log that token at warning level so operators can recover it from startup logs.

#### Scenario: Remote session response exposes bootstrap-token state
- **WHEN** dashboard auth is unconfigured and a non-local client requests `GET /api/dashboard-auth/session`
- **THEN** the response includes `bootstrapRequired: true`
- **AND** it includes `bootstrapTokenConfigured` indicating whether a bootstrap token is currently available

#### Scenario: Auto-generated bootstrap token is logged at warning level
- **WHEN** the service starts with dashboard auth unconfigured and no active bootstrap token
- **THEN** the runtime creates or persists an auto-generated bootstrap token
- **AND** it logs that token at warning level for operator retrieval
