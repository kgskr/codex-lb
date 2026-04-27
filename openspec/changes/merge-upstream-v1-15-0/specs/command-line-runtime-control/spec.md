## ADDED Requirements

### Requirement: Bare CLI invocation runs the foreground server
The CLI MUST run the API server in the foreground when invoked directly and MUST accept the same host, port, and paired TLS flags that upstream `v1.15.0` exposes on the root command.

#### Scenario: Operator runs the bare command
- **WHEN** the operator runs the CLI without a lifecycle subcommand and provides optional `--host`, `--port`, `--ssl-certfile`, or `--ssl-keyfile` flags
- **THEN** the CLI launches the uvicorn server in the current process using the requested bind settings

#### Scenario: TLS flags must be paired
- **WHEN** the operator provides only one of `--ssl-certfile` or `--ssl-keyfile`
- **THEN** the CLI rejects the invocation before starting the server

## REMOVED Requirements

### Requirement: Bare CLI invocation and `serve` both run the foreground server
**Reason**: Upstream `v1.15.0` removes lifecycle subcommands and keeps only direct foreground startup on the root command.
**Migration**: Invoke the CLI directly with `--host`, `--port`, `--ssl-certfile`, and `--ssl-keyfile` instead of using `serve`.

### Requirement: CLI can start a tracked background server
**Reason**: Upstream `v1.15.0` removes the tracked background runtime manager and deletes `app/cli_runtime.py`.
**Migration**: Use an external process supervisor or a separate terminal/session to manage background execution.

### Requirement: CLI reports runtime state for tracked background servers
**Reason**: Upstream `v1.15.0` no longer maintains PID-file-backed lifecycle state for the CLI.
**Migration**: Inspect process state through the chosen external supervisor instead of `status`.

### Requirement: CLI can stop a tracked background server
**Reason**: Upstream `v1.15.0` no longer provides a tracked background shutdown subcommand.
**Migration**: Stop the process through the external supervisor or operating-system process controls instead of `shutdown`.
