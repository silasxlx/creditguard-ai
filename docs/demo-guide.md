# CreditGuard AI PoC Demo Guide

## Prerequisites

1. Windows with Python 3.13, `uv`, Node.js 20+ and npm.
2. Run `uv sync` and `npm.cmd --prefix web ci`.
3. Start the stack with `.\dev.ps1`.
4. Use the synthetic demo identities in the role selector; no real customer data is required.

## Normal path (`DEMO-NORMAL-001`)

1. Keep the role as `RM · 客户经理`.
2. Click `创建正常演示`.
3. Open the case and wait for `等待报告确认`.
4. Switch to `Reviewer · 审查员` and open `报告复核`.
5. Check that the report status is `AWAITING_REVIEW` and the outcome is `PASS`.
6. Confirm the report. The status becomes `CONFIRMED`, and Markdown export is available.

## High-risk path (`DEMO-HIGH-001`)

1. As RM, click `创建高风险演示`.
2. Switch to Reviewer and open `事实复核`.
3. In the `申请期限` conflict, select the `48` month value from `due-diligence.pdf`.
4. Enter a reason such as “尽调报告为最新审查材料，采用其期限值。” and submit.
5. Open `规则与风险`; R07 must be `FAIL`, the risk severity is `HIGH`, and the outcome is `NON_COMPLIANT`.
6. Open `报告复核`, confirm the draft, and verify the report is `CONFIRMED` while remaining clearly labelled as an AI-assisted review.

## Manual upload path

1. As RM, choose `新建案件`.
2. Fill case/customer fields and upload exactly one PDF, DOCX and XLSX set for the four required document types.
3. Submit to create a new immutable material version and Run.
4. Inspect parsing status, progress and any HITL gate.

## Demo API

Only Demo mode exposes the fixed scenario endpoint. It rejects unknown scenario IDs, non-RM users, missing idempotency keys and arbitrary parameters. The endpoint creates real cases, documents and Runs by calling the same services as manual upload.

## Troubleshooting

- If the Worker cannot find policy files, run it from the project root with `$env:PYTHONPATH="$PWD/backend"; uv run python -m app.worker`.
- If a Run is `PAUSED_RETRYABLE`, Reviewer can use the retry action after checking the error category.
- Direct API startup intentionally leaves the Demo route disabled unless the environment flag is set.
