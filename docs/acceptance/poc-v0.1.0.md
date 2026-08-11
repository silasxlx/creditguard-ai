# CreditGuard AI PoC v0.1.0 Acceptance Report

**Status:** VERIFIED candidate; the public repository and release gates are being finalized.

## Scope

The release is a Windows-native, local-only PoC using synthetic cases, five synthetic policy documents and fixed `demo-rm` / `demo-reviewer` identities. It is not a production lending system.

## Evidence summary

| Gate | Result | Evidence |
| --- | --- | --- |
| Backend unit/contract/material tests | PASS | `pytest -p no:cacheprovider`: 25 passed; two warnings only |
| Ruff / Pyright | PASS | local backend checks |
| Frontend type check/build | PASS | `npm.cmd --prefix web run check`, `build` |
| Demo API flag/idempotency | PASS | normal, replay and unknown-scenario smoke |
| Normal browser path | PASS | CI Windows Chromium E2E run `31459709982`; synthetic case reaches `AWAITING_REVIEW` report |
| High-risk browser path | PASS | CI Windows Chromium E2E run `31459709982`; 48-month evidence -> R07 `FAIL` -> `NON_COMPLIANT` -> `CONFIRMED` |
| RM manual upload path | PASS | CI Windows Chromium E2E run `31459709982`; four generated PDF/DOCX/XLSX files upload and start a Run |
| OpenAPI contract export | PASS | `artifacts/openapi.json` and generated TypeScript file |
| External API smoke | NOT RUN IN CI | requires explicit manual workflow and secrets; local deterministic provider remains the default |

## Release metadata

- Generation model configuration: `qwen3.6-flash` (recorded per Run as `model_profile.requested_model`).
- Default CI/PoC provider: deterministic `mock`; no external model or MinerU call is made by ordinary pull requests.
- GitHub Actions evidence: [run 31459709982](https://github.com/silasxlx/creditguard-ai/actions/runs/31459709982).
- All cases and published media are synthetic; no API key, raw provider response, request ID or local machine path is included.

The local browser acceptance used the installed Chrome surface because the bundled Playwright Chromium download was unavailable in this environment. The checked-in Playwright tests remain the CI path; no browser result is claimed from the stalled local runner.

## Safety checks

- No DashScope or MinerU key is committed or uploaded.
- Demo inputs are generated in code and contain no real customer identifiers.
- Report HTML is never injected into the page; Markdown is shown as text.
- Non-Demo mode does not register `/api/v1/demo/scenarios/{scenario_id}`.

## Known limitations

SQLite, local storage and fixed demo users are intentionally PoC choices. Authentication, production tenancy, online deployment, legacy Office formats, arbitrary MCP tools, cancellation and real bank-system integration are future work.
