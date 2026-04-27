# command-line-runtime-control Specification

## Purpose

Define the CLI contract for running the API server in the foreground.

## Requirements

### Requirement: Bare CLI invocation runs the foreground server

The CLI MUST run the API server in the foreground when invoked directly and MUST accept host, port, and paired TLS flags on the root command. The CLI MUST NOT provide tracked background lifecycle subcommands.

#### Scenario: Operator runs the bare command

- **WHEN** the operator runs `codex-lb-cinamon` with optional host, port, or TLS flags
- **THEN** the CLI launches the uvicorn server in the current process using the requested bind settings

#### Scenario: Foreground bind and TLS options are applied

- **WHEN** the operator runs the bare command with `--host`, `--port`, `--ssl-certfile`, or `--ssl-keyfile`
- **THEN** the CLI applies the requested bind and TLS settings to the foreground uvicorn server

#### Scenario: TLS flags must be paired

- **WHEN** the operator provides only one of `--ssl-certfile` or `--ssl-keyfile`
- **THEN** the CLI rejects the invocation before starting the server

#### Scenario: Lifecycle subcommands are rejected

- **WHEN** the operator runs `codex-lb-cinamon serve`, `codex-lb-cinamon start`, `codex-lb-cinamon status`, or `codex-lb-cinamon shutdown`
- **THEN** the CLI rejects the invocation instead of starting or managing a tracked background runtime
