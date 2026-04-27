## ADDED Requirements

### Requirement: Upstream `v1.15.0` merge preserves upgrade paths from local `main`

The merged migration chain MUST support upgrading databases from the current local `main` schema state to the integrated upstream `v1.15.0` schema state without manual stamping or data loss. The merged schema MUST include the upstream additions required for dashboard bootstrap state, durable HTTP bridge sessions, blocked-account tracking, and request-log plan metadata.

#### Scenario: Local main database upgrades to merged head
- **WHEN** a database at the current local `main` migration head is upgraded after the upstream merge
- **THEN** Alembic reaches the merged head successfully
- **AND** the resulting schema contains the upstream structures required by merged auth, proxy, and request-log behavior

### Requirement: Merge integration converges Alembic to one head

The upstream merge MUST end with exactly one Alembic head before merge or release.

#### Scenario: Local and upstream revisions create parallel heads
- **WHEN** the integrated migration graph produces more than one head after bringing in upstream `v1.15.0`
- **THEN** the merge adds an explicit merge revision or equivalent reconciliation step
- **AND** the migration policy check passes with exactly one head
