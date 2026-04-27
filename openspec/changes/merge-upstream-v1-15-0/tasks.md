## 1. Merge Preparation

- [x] 1.1 Create a dedicated integration branch from local `main` for the upstream `v1.15.0` merge.
- [x] 1.2 Capture the `main...v1.15.0` commit inventory and map upstream-only changes into the planned workstreams (schema/auth, CLI/runtime, proxy/provider, frontend).
- [x] 1.3 Inventory local-only `main` behavior that must survive conflict resolution, especially fork-specific routing, auth, and runtime ergonomics.

## 2. Schema And Auth Convergence

- [x] 2.1 Merge upstream Alembic revisions through `v1.15.0` and reconcile the combined graph to a single head.
- [x] 2.2 Apply upstream dashboard bootstrap-token, password-setup, and session-state contract changes without regressing existing local auth behavior.
- [x] 2.3 Reconcile `/api/codex/usage` caller-identity behavior across dashboard auth and API-key validation paths.
- [x] 2.4 Verify upgrade behavior from the current local `main` schema state, including bootstrap state, request-log `planType` metadata, and durable bridge/session tables.
- [x] 2.5 Run targeted auth, bootstrap, and `/api/codex/usage` regression tests against the merged contract.

## 3. CLI And Runtime Surface Alignment

- [x] 3.1 Resolve CLI conflicts so the merged tree explicitly adopts the upstream foreground-only runtime contract and removes tracked background lifecycle subcommands.
- [x] 3.2 Update CLI specs, command parsing, and tests to match the selected post-merge contract.
- [x] 3.3 Run targeted CLI verification for direct startup flags and removed lifecycle behaviors.

## 4. Proxy And Provider Runtime Integration

- [x] 4.1 Resolve upstream proxy admission-control and continuity-recovery conflicts, including reconnect-only replay and `previous_response_id` handling.
- [x] 4.2 Merge sticky-session and bridge owner-handoff behavior so restart/reconnect paths remain deterministic after integration.
- [x] 4.3 Merge provider-routing, built-in Responses tool forwarding, blocked-account recovery, model-registry, and pricing changes required for upstream `gpt-5.5` / `gpt-5.5-pro` support.
- [x] 4.4 Run targeted proxy verification for Responses, websocket, sticky-session, load-balancer, and provider-routing paths.

## 5. Frontend And Contract Alignment

- [x] 5.1 Merge frontend auth/bootstrap, request-log `planType`, and API-key account-availability changes against the merged backend contracts.
- [x] 5.2 Update typed frontend/backend schemas and tests for request-log `planType`, bootstrap session flags, and API key assignment availability.
- [x] 5.3 Run targeted frontend and integration coverage for login/bootstrap flows, dashboard request logs, and API-key settings behavior.

## 6. Final Validation And PR Readiness

- [x] 6.1 Run `openspec validate --specs` and fix any delta-spec or main-spec inconsistencies created by the merge.
- [x] 6.2 Run the local push-gate checks relevant to the merged files (`ruff`, `ty`, targeted `pytest`, CLI tests, and frontend `vitest`); if the host environment is insufficient, rerun the same checks with `podman`.
- [x] 6.3 Review the final merge diff for lost local-only behavior, preserve upstream `v1.15.0` release metadata on the integration branch, record any fork-specific follow-up version bump separately, and prepare the merge PR.
