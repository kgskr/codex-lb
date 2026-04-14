# Command Line Runtime Control Context

## Purpose and Scope

This capability defines how the packaged CLI starts the API server in the foreground or background without requiring shell job control or external supervisors.

See `openspec/specs/command-line-runtime-control/spec.md` for normative requirements.

## Decisions

- Bare invocation remains backward-compatible and maps to the foreground `serve` path.
- `start` launches the server through the same Python environment and module entrypoint instead of introducing a second runtime path.
- Background lifecycle state is tracked through explicit PID metadata rather than process discovery heuristics.

## Constraints

- Default PID and log files live under the runtime directory derived from the configured encryption-key path so packaged installs have one predictable writable home.
- Operators who override `--pid-file` during `start` must pass the same `--pid-file` to `status` and `shutdown` to address the same tracked runtime.
- TLS flags stay symmetrical between foreground and background entrypoints so operators do not need separate bind semantics for `serve` and `start`.

## Failure Modes

- If readiness never succeeds, `start` fails closed, terminates the child process when needed, and removes the PID file.
- If the tracked process disappears unexpectedly, `status` and `shutdown` clean up stale PID metadata instead of reporting a phantom runtime.
- Duplicate tracked starts are rejected so one PID file cannot ambiguously represent multiple live servers.

## Operational Notes

- Readiness probes target `/health/live`.
- Wildcard bind hosts are probed through loopback (`127.0.0.1` for `0.0.0.0`, `::1` for `::`) so local readiness checks still succeed without depending on external routing.
- Background logs are redirected to the tracked log file rather than inheriting the parent terminal.
