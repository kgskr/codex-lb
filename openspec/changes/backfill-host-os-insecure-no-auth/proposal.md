## Why

Fork-local commits added an explicitly insecure host-OS exception that lets requests from the local host network bypass normal remote bootstrap or API-key authentication checks. The behavior is implemented and covered by tests, but OpenSpec never recorded the contract, so the current SSOT understates a high-risk operator-facing mode.

## What Changes

- Document the dashboard-auth exception for host-OS requests when `insecure_allow_remote_no_auth=true`.
- Document the proxy API-key guard bypass for the same host-OS request classification.
- Record the guardrails: host-header spoofing alone is not enough, and dashboard session bypass stops once password or TOTP auth is required.

## Impact

- Operators can see that this mode is intentionally narrow and unsafe by design.
- The main `admin-auth` and `api-keys` specs become consistent with shipped request-locality behavior.
