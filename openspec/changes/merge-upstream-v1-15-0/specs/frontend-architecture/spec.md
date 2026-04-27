## ADDED Requirements

### Requirement: Request logs display account plan tier
When a request log entry is associated with an account, the dashboard request-log API response MUST expose the persisted request-log `planType` snapshot, and the recent-requests table MUST render the plan tier in a visible request-log column or badge.

#### Scenario: Request log entry keeps its original plan type snapshot
- **WHEN** a request log entry is written while the associated account's `plan_type` is `free`
- **AND** the account later changes to `team`
- **THEN** the `GET /api/request-logs` response still includes `planType: "free"` for that row
- **AND** the dashboard recent-requests table renders the original `free` plan tier visibly for that row

#### Scenario: Legacy request log entry without account still renders
- **WHEN** a request log entry has no related account
- **THEN** the `GET /api/request-logs` response includes `planType: null` or omits it
- **AND** the dashboard recent-requests table still renders the row without failing

### Requirement: API key assignment picker shows availability metadata

The settings page MUST surface current account availability metadata for API key assignment flows so operators can tell whether a selected account is currently usable before saving or editing an assignment.

#### Scenario: API key assignment picker shows availability metadata
- **WHEN** the settings page loads account options for API key assignment
- **THEN** each option renders the availability state returned by the backend
- **AND** unavailable accounts remain distinguishable without removing them from the picker
