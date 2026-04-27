## ADDED Requirements

### Requirement: API key assignment surfaces current account availability

The API key management flow MUST expose availability metadata for assignable accounts so operators can tell whether a selected account is currently usable before saving or editing an API key assignment.

#### Scenario: API key editor shows account availability
- **WHEN** an operator opens the create or edit flow for an API key assignment
- **THEN** the returned account options include current availability state
- **AND** the picker renders that state alongside the account label

#### Scenario: Existing unavailable assignment remains visible
- **WHEN** an API key is already assigned to an account that later becomes unavailable
- **THEN** the edit flow still shows the assigned account
- **AND** it marks the account as unavailable instead of silently dropping the assignment
