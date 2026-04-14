## Context

현재 compact 요청은 contract 보존을 위해 일반 `/responses`와 분리되어 있고, ChatGPT upstream의 `/codex/responses/compact` 를 직접 호출하도록 설계되어 있습니다. 이 분리는 맞지만, mixed-provider routing 쪽에서는 compact를 phase-1 fallback 대상에서 제외해 두어서 ChatGPT-web 풀이 모두 rate-limited 된 상황에서도 `openai_platform`으로 우회하지 못하고 바로 `503`으로 끝납니다.

이미 일반 HTTP `/v1/responses` 와 `/backend-api/codex/responses` 는 Platform fallback을 지원합니다. 따라서 이번 변경의 핵심은 compact의 contract 분리를 유지하면서 provider 선택만 확장하는 것입니다.

추가 전제:

- `backend_codex_http` 와 `public_responses_http` route family는 그대로 유지한다.
- `openai_platform` identity는 UI/API에서 route family를 개별 선택하지 않고, phase-1에서 지원되는 route family 전체를 항상 활성화한다.
- compact는 기존처럼 opaque compact payload를 canonical next context window로 취급한다.
- OpenAI Platform은 2026-04-13 기준 공식 API reference에 `/v1/responses/compact` endpoint를 문서화하고 있으므로, Platform compact fallback은 provider-native compact contract 위에서 설계할 수 있다.

## Goals / Non-Goals

**Goals:**

- ChatGPT-web 풀이 drained 되었을 때 `/v1/responses/compact` 와 `/backend-api/codex/responses/compact` 도 Platform fallback을 탈 수 있게 한다.
- compact 성공 결과는 provider-native compact payload 그대로 반환한다.
- backend Codex compact 요청이 Platform으로 fallback 될 때도 request logging, API key settlement, affinity, retry semantics를 유지한다.
- websocket이나 continuity-dependent request shape는 계속 fail-closed 한다.

**Non-Goals:**

- compact를 일반 `/responses`로 재작성하거나 surrogate fallback을 도입하지 않는다.
- websocket `/responses` fallback을 추가하지 않는다.
- 새로운 route family를 추가하지 않는다.
- provider capability가 불명확한 continuity semantics를 phase 1에서 억지로 지원하지 않는다.

## Decisions

### 1. Compact fallback은 기존 responses route family에 포함시키고 Platform identity는 지원 경로 전체를 항상 사용한다

새 route family를 만들지 않고, `public_responses_http` 는 `/v1/responses` 와 `/v1/responses/compact` 를, `backend_codex_http` 는 `/backend-api/codex/responses` 와 `/backend-api/codex/responses/compact` 를 함께 포함하도록 해석한다.
운영자는 route family를 개별적으로 고르지 않으며, 등록된 `openai_platform` identity는 phase-1 지원 route family 전체에 대해 동일한 fallback 후보가 된다.

이유:

- dashboard와 storage schema를 유지할 수 있다.
- path 선택 UI 없이도 route policy가 예측 가능해지고, Codex app/CLI + OpenAI-compatible compact fallback 범위를 누락 없이 제공할 수 있다.
- compact 전용 policy를 route family 레벨이 아니라 provider capability 레벨에서 좁히는 편이 현재 구조와 맞다.

대안:

- compact 전용 route family 추가: 정책은 세밀해지지만 UI, schema, migration 비용이 커서 과하다.

### 2. Provider selection은 확장하되 compact transport는 provider-native endpoint만 호출한다

ChatGPT upstream이 선택되면 기존 `/codex/responses/compact` 경로를 그대로 사용한다. `openai_platform`이 선택되면 public OpenAI `/v1/responses/compact` 를 직접 호출한다. 어느 경우든 compact payload는 opaque pass-through로 유지한다.

이유:

- compact는 provider-owned contract라서 일반 `/responses`로 바꾸면 의미가 깨진다.
- Platform compact fallback을 넣더라도 “선택된 provider의 compact endpoint를 직접 호출한다”는 규칙만 지키면 contract 분리를 유지할 수 있다.

대안:

- Platform compact를 일반 `/v1/responses`로 대체: contract가 달라져 잘못된 context window를 만들 수 있으므로 제외.

### 3. Backend Codex compact fallback은 public Platform compact contract로 번역한다

`/backend-api/codex/responses/compact` 는 downstream path이고, Platform에는 backend-private compact contract가 없다. 따라서 Platform이 선택되면 payload를 public Platform compact request shape로 정규화한 뒤 `/v1/responses/compact` 로 보낸다. 응답은 downstream client에 compact payload 그대로 반환한다.

이유:

- backend Codex client가 원하는 것은 compact 결과이지 backend-private upstream shape 자체가 아니다.
- 기존 backend HTTP responses fallback도 public Platform contract translation으로 동작한다.

대안:

- backend compact는 fallback 금지 유지: 현재 사용자 장애를 해결하지 못한다.

### 4. Compact capability gating은 request shape와 provider support를 함께 본다

compact fallback은 stateless compact request에서만 허용한다. provider가 compact endpoint를 지원하지 않거나, request shape가 compact contract 밖으로 벗어나면 fail-closed 한다. backend Codex session headers는 affinity 힌트로는 유지하되, unsupported continuity semantics를 암묵적으로 에뮬레이션하지 않는다.

이유:

- compact는 continuity를 압축한 결과를 다루는 contract이지, 임의의 continuity 재현 레이어가 아니다.
- 기존 backend HTTP fallback 원칙과 같은 방향으로 유지할 수 있다.

### 5. Retry와 observability는 provider-aware compact path에도 동일하게 적용한다

same-contract bounded retry, request log transport, provider kind, error code/message, fallback selection reason, API key settlement는 Platform compact path에도 동일하게 남긴다.

이유:

- compact fallback이 추가되면 “왜 compact가 Platform으로 갔는지”, “어느 provider compact endpoint에서 실패했는지”가 로그에 남아야 운영이 가능하다.

## Risks / Trade-offs

- [Platform compact contract 세부 shape 차이] → ChatGPT compact payload와 Platform compact payload가 구조적으로 다를 수 있으므로, parsing/validation을 최소화하고 opaque pass-through를 유지한다.
- [모델 지원 차이] → ChatGPT와 Platform에서 compact 지원 모델이 다를 수 있으므로 provider capability/model discovery 체크를 compact 경로에도 적용한다.
- [backend client 기대 shape 차이] → backend Codex client가 특정 ChatGPT-private compact 필드를 기대하면 Platform compact 결과와 차이가 날 수 있다. 우선 canonical compact contract를 기준으로 호환성을 검증하고, 필요한 차이는 별도 follow-up으로 분리한다.
- [오탐 fallback] → compact도 fallback 대상이 되면 drained 판단이 더 중요해지므로 기존 usage-threshold 규칙과 health recording을 그대로 재사용하고 회귀 테스트를 추가한다.
