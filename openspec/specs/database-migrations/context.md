## Overview

`database-migrations` capability defines how codex-lb evolves schema safely across fresh installs, partially migrated legacy DBs, and ongoing branch development.

## Scope and Non-Goals

- Scope:
  - Runtime startup migration behavior
  - Legacy history bootstrap/remap behavior
  - Revision naming and head governance
  - CI migration guardrails
- Non-goals:
  - Designing rollback SQL for every migration
  - Supporting alternate revision ID formats
  - Maintaining compatibility with unknown third-party Alembic revisions

## Key Decisions

- Alembic is the runtime SSOT for migrations.
- Revision IDs use `YYYYMMDD_HHMMSS_slug` for readability and merge-conflict reduction.
- Legacy IDs are auto-remapped at startup to avoid manual DB patching during cutover.
- Legacy remaps target the latest safe predecessor revision when a later-looking legacy ID does not prove that newly inserted branch migrations have already run.
- CI checks both policy (head/naming) and drift in one command path.

## Constraints

- Legacy `schema_migrations` rows are historical input only.
- Production rollout assumes one migration executor at a time.
- Unsupported `alembic_version` IDs fail fast to avoid silent divergence.
- Startup also verifies post-upgrade schema drift before the app begins normal work.

## Failure Modes and Mitigations

- Multiple Alembic heads caused by parallel branches:
  - Mitigation: CI fails; add merge revision before merge/release.
- Legacy revision IDs still present in operator DB:
  - Mitigation: startup auto-remap of known IDs to a current revision that still lets missing downstream migrations execute.
- Additive compatibility migration downgrade could remove an operator-owned nullable column:
  - Mitigation: downgrade removes only migration-owned indexes/constraints when column ownership cannot be proven.
- Unknown revision IDs in `alembic_version`:
  - Mitigation: explicit startup failure + manual operator intervention.
- Drift between metadata and migrated schema:
  - Mitigation: CI unified migration check blocks merge.
  - Runtime mitigation: startup drift check logs explicit diffs and fails startup when `database_migrations_fail_fast=true`.

## Operational Notes

- Startup path:
  - inspect state -> (optional SQLite backup) -> bootstrap legacy `schema_migrations` -> remap legacy Alembic IDs -> `upgrade head` -> schema drift check
- CLI checks:
  - `codex-lb-db check` validates head count, revision naming/filename policy, and schema drift.
- Emergency toggle:
  - `CODEX_LB_DATABASE_ALEMBIC_AUTO_REMAP_ENABLED=false` disables auto-remap.

## Example

Branch A and B each create migration revisions in parallel. After merge, CI detects multiple heads and fails. The resolver adds a merge revision, reruns CI, and proceeds. During deployment, a DB still storing old `013_add_dashboard_settings_routing_strategy` in `alembic_version` is auto-remapped to `20260225_000000_add_dashboard_settings_routing_strategy` before upgrade.

For a legacy row such as `20260410_020000_restore_import_without_overwrite_default_false`, the remap points at the last safe pre-bridge merge revision so the HTTP bridge table migrations still run during `upgrade head`.
