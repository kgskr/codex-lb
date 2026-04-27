# codex-lb Helm 안내

이 포크는 컨테이너 배포를 기준으로 유지되며, Helm/Kubernetes 배포 문서는 더 이상 적극적으로 관리하지 않습니다.

권장 배포 방식:

```bash
docker run -d --name codex-lb \
  -p 2455:2455 -p 1455:1455 \
  -v codex-lb-data:/var/lib/codex-lb \
  ghcr.io/cinev/codex-lb-cinamon:latest
```

필요한 정보는 최상위 `README.md`를 기준으로 확인하면 됩니다.

Helm 템플릿과 값 파일은 저장소에 남아 있지만, 이 포크에서는 Helm/Kubernetes 배포 절차를 최신 기준으로 보장하지 않습니다. 차트 자체를 참고해야 한다면 `deploy/helm/codex-lb/` 아래 템플릿과 values 파일을 직접 확인하세요.

차트 메타데이터의 최소 Kubernetes 버전은 `1.32`입니다. CI의 차트 검증은 `1.35` 렌더링 기준을 사용합니다.

`values-prod.yaml`은 External Secrets 모드를 켭니다. 이 overlay를 직접 렌더링하거나 배포할 때는 운영 환경의 SecretStore 또는 ClusterSecretStore 이름을 반드시 전달해야 합니다.

```bash
helm template codex-lb deploy/helm/codex-lb \
  -f deploy/helm/codex-lb/values-prod.yaml \
  --set externalSecrets.secretStoreRef.name=<secret-store-name>
```

ClusterSecretStore를 쓸 때는 kind도 같이 넘겨야 합니다.

```bash
helm template codex-lb deploy/helm/codex-lb \
  -f deploy/helm/codex-lb/values-prod.yaml \
  --set externalSecrets.secretStoreRef.name=<cluster-secret-store-name> \
  --set externalSecrets.secretStoreRef.kind=ClusterSecretStore
```

External Secrets backend의 remote secret key는 Helm fullname과 같아야 합니다. 기본 release 이름 `codex-lb`에서는 remote key가 `codex-lb`이고, `fullnameOverride`를 쓰면 그 값으로 바뀝니다. remote secret에는 `database-url`과 `encryption-key` property가 있어야 하며, 이 값들이 생성되는 Kubernetes Secret의 `database-url`/`encryption-key`로 매핑됩니다.

Responses 전용 Ingress는 exact path 매칭을 기준으로 `/v1/responses`, `/v1/responses/compact`, `/backend-api/codex/responses`, `/backend-api/codex/responses/compact`를 별도로 라우팅합니다.
