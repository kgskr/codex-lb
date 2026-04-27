## Why

Local `main` has diverged from upstream `v1.15.0` across proxy runtime behavior, dashboard authentication, frontend surfaces, and Alembic history. A direct merge without an explicit plan would make it easy to miss required spec updates, migration-head reconciliation, or regression coverage in conflict-heavy areas.

This change captures the merge plan as an OpenSpec work item so the upstream `v1.13.0` through `v1.15.0` behavior can be imported into local `main` in a controlled, verifiable sequence.

## What Changes

- Define the upstream merge scope from local `main` to upstream `v1.15.0`, including auth/bootstrap, `/api/codex/usage` caller-identity behavior, CLI lifecycle changes, proxy continuity and admission control, provider-routing/model updates, dashboard/frontend changes, and database migration convergence.
- Record which existing capabilities must be updated to reflect adopted upstream behavior before implementation starts.
- Break the merge into ordered workstreams with explicit validation gates for migrations, backend tests, frontend tests, and spec sync.
- Capture rollback and conflict review checkpoints for areas with the highest merge risk, especially auth/usage exceptions, CLI/runtime conflicts, proxy service flows, request continuity, and Alembic heads.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `admin-auth`: Align remote bootstrap-token setup, session bootstrap flags, proxy auth mode hardening, and `/api/codex/usage` caller-identity behavior with upstream `v1.15.0`.
- `api-keys`: Incorporate upstream API key assignment UX changes and any merge-time contract adjustments required by the new dashboard flows.
- `command-line-runtime-control`: Decide and document whether the merged tree adopts upstream foreground-only CLI behavior or preserves local lifecycle subcommands.
- `database-migrations`: Reconcile upstream Alembic revisions and merge-head behavior with the current local migration chain.
- `frontend-architecture`: Adopt upstream dashboard/login/settings UI behavior that supports remote bootstrap, request-log `planType` visibility, and API key account availability.
- `responses-api-compat`: Import upstream Responses continuity, replay, built-in tool forwarding, input-trimming, and model-catalog behavior.
- `sticky-session-operations`: Align sticky defaults and durable bridge/session ownership behavior with upstream continuity fixes.
- `upstream-provider-management`: Incorporate upstream routing policy, quota recovery, blocked-account handling, and new model support through `v1.15.0`.

## Impact

- Upstream merge preparation for `main` through tag `v1.15.0`
- CLI/runtime surface under `app/cli.py`, `app/cli_runtime.py`, and related tests/specs
- Backend modules under `app/core/**` and `app/modules/**`, especially auth, proxy, routing, and usage paths
- Frontend dashboard/settings/auth flows under `frontend/src/**`
- Alembic revisions and migration validation under `app/db/**`
- Regression coverage under `tests/**`
- OpenSpec deltas and validation for the affected capabilities
