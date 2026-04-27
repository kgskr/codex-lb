## ADDED Requirements

### Requirement: Bridge owner handoff preserves durable session continuity across restart

The merged HTTP bridge lifecycle MUST allow a durable session owner to reconnect or restart without breaking the session's sticky routing contract. Ownership handoff MUST remain deterministic and MUST NOT expose internal bridge-topology details in client-visible failures.

#### Scenario: Reconnect-only bridge recovery keeps the session sticky
- **WHEN** the current bridge owner loses the upstream connection but the session can recover on the same logical owner
- **THEN** the service preserves the durable sticky mapping for that session
- **AND** later turns continue on the recovered owner without requiring a new session id

#### Scenario: Shutdown or restart hands off ownership deterministically
- **WHEN** the active bridge owner shuts down or restarts while a durable bridged session still exists
- **THEN** a deterministic owner-handoff path restores the session
- **AND** client-visible errors do not expose internal bridge-topology identifiers

### Requirement: Merged defaults backfill sticky and reset settings safely

When the upstream merge introduces new default values for sticky-thread and reset-preference settings, the system MUST backfill missing legacy dashboard settings rows with those defaults without overriding operator-selected values.

#### Scenario: Legacy settings row is backfilled with merged defaults
- **WHEN** an upgraded installation lacks explicit persisted values for the merged sticky-thread or reset-preference settings
- **THEN** the migration or bootstrap path stores the upstream default values
- **AND** later requests observe those defaults without manual operator intervention

#### Scenario: Explicit operator settings are preserved
- **WHEN** an upgraded installation already has explicit sticky-thread or reset-preference values
- **THEN** the merge keeps those existing values
- **AND** it does not overwrite them with upstream defaults
