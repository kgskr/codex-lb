# deployment-networking Context

## Purpose

`deployment-networking` captures Kubernetes networking behavior that affects whether traffic can safely reach codex-lb during install, migration, and steady-state serving.

## Decisions

- NetworkPolicy defaults stay fail-closed. Operators must explicitly allow namespace ingress when they want cross-namespace access.
- The Responses dedicated Ingress uses exact paths because the chart may apply route-specific timeout, hashing, and upstream balancing annotations.
- Compact Responses routes are part of the same dedicated ingress surface as standard Responses routes.

## Constraints

- Exact path matching avoids accidental capture of unrelated `/v1/*` or `/backend-api/*` routes.
- Exact path matching also means every supported leaf route must be listed explicitly.
- Backend Codex and public OpenAI-compatible Responses paths must stay in sync when compact support is enabled.

## Failure Modes

- Missing `/v1/responses/compact` or `/backend-api/codex/responses/compact` from a dedicated exact-path ingress sends compact traffic to the wrong ingress or no ingress at all.
- Overly broad ingress paths can bypass route-specific annotations and break session-affinity or timeout expectations.

## Example

A production chart using `ingress.responsesDedicated.enabled=true` should render exact paths for `/v1/responses`, `/v1/responses/compact`, `/backend-api/codex/responses`, and `/backend-api/codex/responses/compact` under the dedicated Responses Ingress.
