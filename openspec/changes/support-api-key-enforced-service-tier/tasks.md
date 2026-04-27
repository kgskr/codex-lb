## 1. Specs

- [x] 1.1 Add API key enforcement requirements for service tier persistence and alias handling.
- [x] 1.2 Validate OpenSpec changes.

## 2. Tests

- [x] 2.1 Add unit coverage for service tier normalization and persistence.
- [x] 2.2 Add integration coverage for dashboard CRUD and proxy enforcement.

## 3. Implementation

- [x] 3.1 Add `enforced_service_tier` to DB/API/service layers.
- [x] 3.2 Apply enforced service tier to proxied requests with `fast -> priority` normalization.
