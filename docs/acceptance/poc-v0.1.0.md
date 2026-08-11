# CreditGuard AI PoC v0.1.0 Acceptance Report

**Status:** implementation evidence collected; release gates remain local until the public GitHub repository is created.

## Scope

The release is a Windows-native, local-only PoC using synthetic cases, five synthetic policy documents and fixed `demo-rm` / `demo-reviewer` identities. It is not a production lending system.

## Evidence summary

| Gate | Result | Evidence |
| --- | --- | --- |
| Backend unit/contract/material tests | PASS | `pytest -p no:cacheprovider` targeted suite: 14 passed; full suite recorded during release run |
| Ruff / Pyright | PASS | local backend checks |
| Frontend type check/build | PASS | `npm.cmd --prefix web run check`, `build` |
| Demo API flag/idempotency | PASS | normal, replay and unknown-scenario smoke |
| Normal browser path | PASS | synthetic case reaches `AWAITING_REVIEW` report |
| High-risk browser path | PASS | 48-month evidence -> R07 `FAIL` -> `NON_COMPLIANT` -> `CONFIRMED` |
| OpenAPI contract export | PASS | `artifacts/openapi.json` and generated TypeScript file |
| External API smoke | NOT RUN IN CI | requires explicit manual workflow and secrets |

The local browser acceptance used the installed Chrome surface because the bundled Playwright Chromium download was unavailable in this environment. The checked-in Playwright tests remain the CI path; no browser result is claimed from the stalled local runner.

## Safety checks

- No DashScope or MinerU key is committed or uploaded.
- Demo inputs are generated in code and contain no real customer identifiers.
- Report HTML is never injected into the page; Markdown is shown as text.
- Non-Demo mode does not register `/api/v1/demo/scenarios/{scenario_id}`.

## Known limitations

SQLite, local storage and fixed demo users are intentionally PoC choices. Authentication, production tenancy, online deployment, legacy Office formats, arbitrary MCP tools, cancellation and real bank-system integration are future work.
