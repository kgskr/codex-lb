## Context

Local `main` and upstream `v1.15.0` have diverged in both history and behavior. The upstream-only range introduces changes across dashboard bootstrap/auth flows, proxy admission and continuity recovery, request-log surfaces, model catalog support, and multiple Alembic revisions. The local fork also carries its own history and naming/versioning choices, so a blind merge would create high conflict density in `app/modules/proxy/**`, `app/core/auth/**`, `app/db/**`, `frontend/src/**`, and related tests.

This change is planning work, not the merge itself. The design therefore focuses on how to integrate the upstream tag into local `main` with explicit checkpoints that protect existing local behavior while adopting upstream `v1.15.0` capabilities intentionally.

## Goals / Non-Goals

**Goals:**
- Use upstream tag `v1.15.0` as the fixed integration target for local `main`.
- Resolve the merge in workstreams that match the real conflict boundaries: schema/auth, CLI/runtime surface, proxy runtime, provider/model catalog, and frontend.
- Define validation gates that prove the merged tree is safe to push, including OpenSpec validation, targeted backend/frontend tests, and migration checks.
- Preserve or consciously reconcile local-only behavior instead of accidentally dropping it during conflict resolution.

**Non-Goals:**
- Implement any upstream changes newer than `v1.15.0`.
- Rewrite existing local architecture beyond what is needed to land the upstream merge safely.
- Clean up unrelated documentation, contributor metadata, or refactors that do not affect merge correctness.
- Bump the fork to a post-`v1.15.0` release version as part of this merge; that is follow-up work after the upstream-aligned integration lands.

## Decisions

### Use `v1.15.0` as the merge anchor

The merge plan uses the release tag instead of floating `upstream/main` so the scope is stable and reviewable.

- Chosen: merge against fixed tag `v1.15.0`
- Alternative considered: merge latest `upstream/main`
- Why not the alternative: it would let the target move while conflicts are being resolved and would make verification non-repeatable

### Merge on top of local `main` in a dedicated integration branch

The implementation should start from local `main`, create a dedicated merge branch, and bring the upstream tag into that branch.

- Chosen: one integration branch rooted at local `main`
- Alternative considered: cherry-pick release commits or rebase local `main` onto upstream history
- Why not the alternative: cherry-picking loses conflict context across related commits, and rebasing fork history makes rollback and review harder

### Preserve upstream `v1.15.0` release metadata during the merge

This merge plan adopts upstream `v1.15.0` version semantics as-is on the integration branch. Any fork-specific version bump happens only after the upstream-aligned merge is stable.

- Chosen: keep upstream `v1.15.0` release/version metadata in the merge branch
- Alternative considered: bump to the next fork version during the same merge
- Why not the alternative: it expands scope, makes conflict review noisier, and obscures whether regressions come from the merge or from fork-specific release edits

### Resolve schema, auth, and CLI contracts before proxy and frontend conflicts

Alembic heads, dashboard bootstrap state, auth response shapes, and the CLI lifecycle contract drive later proxy and frontend work. Those contracts should be stabilized before resolving the largest proxy-service diffs.

- Chosen: workstream order of migrations/auth/CLI first, then proxy/provider, then frontend
- Alternative considered: resolve proxy runtime first because it contains most of the diff
- Why not the alternative: proxy tests and frontend integration will keep churning if the schema and auth contracts are still moving

### Treat proxy continuity and provider-routing behavior as the primary risk area

Most functional risk sits in the proxy service, bridge lifecycle, routing thresholds, and `previous_response_id` handling. That area should be merged in smaller reviewable commits with targeted verification after each sub-step.

- Chosen: split proxy integration into admission/continuity, sticky/bridge lifecycle, and provider/model updates
- Alternative considered: resolve all proxy conflicts in one pass and validate only at the end
- Why not the alternative: regressions would be harder to localize and rollback

### Use local CI-equivalent checks as the merge gate

The push gate should be the repo's local checks. If the host environment is insufficient, the plan should run the relevant tests with `podman` rather than skipping validation.

- Chosen: validate with `openspec validate --specs`, targeted Python tests, frontend tests, and migration checks before push
- Alternative considered: rely on remote CI after opening the merge PR
- Why not the alternative: it delays detection of predictable merge breakage and violates the repo's push-validation rule

## Risks / Trade-offs

- [CLI contract regression] -> Decide the foreground-only vs lifecycle-subcommand contract up front, reflect it in OpenSpec, and run targeted CLI tests before proxy/front-end cleanup.
- [Proxy service conflict density] -> Resolve `app/modules/proxy/**` in smaller workstream commits and run targeted Responses, websocket, and load-balancer tests after each step.
- [Alembic head divergence] -> Inspect the merged revision graph immediately after schema conflict resolution and add an explicit merge revision before moving on.
- [Auth exception-path drift] -> Lock down bootstrap setup and `/api/codex/usage` caller-identity contracts before touching dependent frontend or proxy code, then run targeted auth regression tests.
- [Frontend/backend contract drift] -> Merge request-log, bootstrap, and API-key UI work only after the corresponding backend schemas are settled; run frontend tests against the merged contracts.
- [Local fork behavior loss] -> Compare local-only `main` commits against the merged tree before finalizing; reapply any intentionally retained fork behavior in follow-up commits instead of assuming the merge kept it.

## Migration Plan

1. Create a dedicated integration branch from local `main`.
2. Merge upstream tag `v1.15.0` into that branch without squashing.
3. Reconcile Alembic revisions, bootstrap/auth flows, `/api/codex/usage` auth behavior, and request-log schema changes first.
4. Resolve CLI lifecycle conflicts so the merged tree explicitly adopts the upstream foreground-only runtime contract.
5. Resolve proxy continuity, admission control, sticky-session, built-in tool forwarding, and provider-routing conflicts in isolated commits.
6. Resolve frontend contract and UI conflicts for remote bootstrap flows, request-log `planType` display, and API key account availability.
7. Reconcile model registry, pricing, and remaining fixtures while preserving upstream `v1.15.0` release/version metadata.
8. Run `openspec validate --specs` plus targeted backend/frontend/CLI checks; if the host environment is insufficient, rerun the same checks under `podman`.
9. Open the merge PR only after the merged tree has one Alembic head and passing local verification.

Rollback strategy:
- Before push, discard the integration branch or revert the merge commit if the combined tree proves unstable.
- After proxy workstream validation failures, revert only the last isolated resolution commit and retry rather than restarting the full merge.

## Open Questions

- Which local-only behaviors on current `main` are authoritative if they conflict with upstream `v1.15.0`, especially around platform fallback policy and CLI/runtime ergonomics?
- Is the preferred review shape one large merge commit plus follow-up fix commits, or a staged merge branch with several conflict-resolution commits before the final PR?
