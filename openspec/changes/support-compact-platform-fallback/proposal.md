## Why

현재 Platform fallback은 일반 HTTP `/responses` 계열까지만 지원하고, `/backend-api/codex/responses/compact` 와 `/v1/responses/compact` 는 명시적으로 제외되어 있습니다. 그래서 Codex app/CLI가 compact 요청을 보내는 순간 ChatGPT-web 풀이 전부 rate limit 또는 cooldown 상태여도 Platform API key로 우회하지 못하고 바로 `503 Rate limit exceeded` 로 실패합니다.

## What Changes

- `openai_platform` fallback 범위를 compact Responses 경로까지 확장합니다.
- `openai_platform` identity 등록/수정 시 route family 선택을 제거하고, 지원되는 phase-1 경로군 전체를 항상 활성화합니다.
- compact 요청도 ChatGPT 풀이 drained 되었을 때 Platform fallback 후보로 평가되도록 라우팅 정책을 확장합니다.
- compact 요청에서 Platform으로 넘길 수 없는 continuity-dependent 또는 provider-specific payload가 있으면 기존처럼 fail-closed 하되, 단순 stateless compact 요청은 Platform으로 전달할 수 있게 계약을 명확히 합니다.
- dashboard와 운영 문서에서 compact fallback 지원 범위와 제한사항을 명확히 설명합니다.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `upstream-provider-management`: `openai_platform` route eligibility와 fallback 정책이 compact Responses 경로까지 확장됩니다.
- `responses-api-compat`: compact Responses 요청의 provider-aware routing, fallback ordering, 오류 처리, contract preservation 요구사항이 변경됩니다.

## Impact

- 영향 코드: compact route gating, provider capability 판정, compact transport adapter, Platform request translation, compact request validation/selection, 관련 request logging
- 영향 API: `POST /backend-api/codex/responses/compact`, `POST /v1/responses/compact`
- 영향 테스트: compact integration tests, Platform fallback integration tests, load balancer/provider capability tests
- 운영 영향: Codex app/CLI의 compact task가 ChatGPT-web rate limit 상태에서도 Platform API key로 계속 진행될 수 있음
