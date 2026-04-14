## MODIFIED Requirements

### Requirement: Session authentication guard

The system SHALL enforce session authentication on `/api/*` routes except `/api/dashboard-auth/*`. Authentication SHALL be enforced via a router-level dependency guard, not ASGI middleware.

When `insecure_allow_remote_no_auth=true` and the request is positively identified as originating from the host OS network, the guard MAY bypass session enforcement for non-`/api/dashboard-auth/*` routes only while dashboard auth is otherwise disabled (`password_hash` is NULL and `totp_required_on_login` is false). Host-header spoofing alone MUST NOT qualify a request for this bypass.

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

### Requirement: Session state endpoint

The system SHALL expose `GET /api/dashboard-auth/session` returning the current authentication state including `password_required`, `authenticated`, `totp_required_on_login`, `totp_configured`, and bootstrap flags used for first-run remote setup.

#### Scenario: Host-OS request reports authenticated bootstrap-free state

- **WHEN** `password_hash` is NULL and `totp_required_on_login` is false
- **AND** `insecure_allow_remote_no_auth=true`
- **AND** the request is classified as a host-OS request
- **THEN** the session response reports `authenticated: true`
- **AND** it reports `bootstrapRequired: false`
