## 1. Routing and capability gating

- [x] 1.0 Remove operator-facing Platform route-family selection and force all phase-1 supported route families on create/update.
- [x] 1.1 Extend provider capability and route-family eligibility checks so `public_responses_http` and `backend_codex_http` can admit compact requests when the selected provider supports compact fallback.
- [x] 1.2 Update compact route gating in the proxy API/service so Platform fallback is no longer rejected up front for eligible stateless compact requests.
- [x] 1.3 Preserve fail-closed behavior for websocket or other unsupported continuity-dependent request shapes while allowing stateless compact fallback.

## 2. Compact transport and translation

- [x] 2.1 Add an `openai_platform` compact transport path that calls the public OpenAI `/v1/responses/compact` endpoint directly.
- [x] 2.2 Translate backend Codex compact requests onto the Platform compact contract without rewriting the returned compact payload.
- [x] 2.3 Keep compact same-contract retry, affinity, request logging, and API key settlement behavior intact across both ChatGPT and Platform providers.

## 3. Verification and operator guidance

- [x] 3.1 Add unit and integration coverage for `/v1/responses/compact` and `/backend-api/codex/responses/compact` fallback after the ChatGPT pool is drained.
- [x] 3.2 Add regression coverage showing compact requests still fail closed for unsupported provider/continuity combinations.
- [x] 3.3 Update operator-facing docs/context to explain that compact fallback is supported only for eligible stateless compact HTTP routes.
