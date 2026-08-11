# 授信智能合规审查平台 PoC 接口与数据契约 V1.0

**编号：SPEC-004**  
**版本：V1.0**  
**状态：APPROVED**  
**评审结论：2026-08-10 用户评审通过**  
**业务范围：[SPEC-002](./SPEC-002-credit-review-poc-scope-v1.md)**  
**技术架构：[SPEC-003](./SPEC-003-credit-review-architecture-poc-v1.md)**

---

## 1. 契约原则

- `/api/v1` 为 PoC 唯一 API 版本；V1 内只做向后兼容变更，版本迁移机制不在 PoC 范围。
- FastAPI/Pydantic OpenAPI 是接口单一来源，并生成 TypeScript 类型。
- 金额使用十进制字符串，日期使用 ISO 8601，时间使用带时区 UTC 时间。
- ID 使用不透明 UUID 字符串；写操作带 `Idempotency-Key`，并发人工决策带 `expected_snapshot_version`。
- 历史 Run、材料版本、快照和人工决策不可变；更正通过新版本表达。
- 错误统一使用 Problem Details，不返回堆栈、密钥、完整模型响应或本机绝对路径。

## 2. 演示身份与分页

```text
X-Demo-User-Id: demo-rm | demo-reviewer
```

后端固定映射 `demo-rm=RM`、`demo-reviewer=REVIEWER`。未知用户返回 401，有身份但越权返回 403，客户端提交的 role 不参与授权。

列表接口使用 `cursor` 与 `limit`，`limit` 默认 20、最大 100；排序固定为 `created_at DESC, id DESC`。响应为 `items`、`next_cursor`，游标不透明。

## 3. 资源 Schema

```text
CaseCreateRequest
  case_no: string
  customer_name: string
  customer_key: string
  review_date: date

CaseResponse
  id, case_no, customer_name, customer_key, review_date
  version: integer
  created_by, created_at, updated_at

DocumentResponse
  id, case_id, document_type, version, active
  original_filename, content_hash, mime, size_bytes, status
  replaces_document_id?, created_at

RunCreateRequest
  document_version_ids: string[]
  expected_case_version: integer

RunResponse
  id, case_id, status, stage, progress_percent
  waiting_gate?, retryable, pause_reason?, error_code?
  input_document_version_ids
  workflow_version, rule_pack_version, policy_pack_version
  policy_index_version, prompt_versions, model_profile
  allowed_actions, created_at, updated_at
```

创建 Run 时必须明确提交活动材料版本 ID，且四类必需材料各恰好一个；版本必须属于该案件、状态可用且与 `expected_case_version` 一致。材料变化不修改旧 Run，只能创建新 Run。

## 4. REST API

| 方法与路径 | 角色 | 成功码 | 请求/响应 |
|---|---|---:|---|
| `POST /cases` | RM | 201 | `CaseCreateRequest → CaseResponse` |
| `GET /cases` | RM/Reviewer | 200 | 分页 `CaseResponse` |
| `GET /cases/{case_id}` | RM/Reviewer | 200 | 案件、活动材料与 Run 摘要 |
| `POST /cases/{case_id}/documents` | RM | 201 | multipart：`document_type`、`file`、可选 `replaces_document_id`；返回 `DocumentResponse` |
| `GET /cases/{case_id}/documents` | RM/Reviewer | 200 | 分页材料版本，支持 `active_only` |
| `POST /cases/{case_id}/runs` | RM | 202 | `RunCreateRequest → RunResponse` |
| `GET /runs/{run_id}` | RM/Reviewer | 200 | `RunResponse` |
| `POST /runs/{run_id}/retry` | RM/Reviewer | 202 | `RetryRequest → RunResponse` |
| `GET /runs/{run_id}/facts` | Reviewer | 200 | `FactReviewView` |
| `POST /runs/{run_id}/fact-review` | Reviewer | 200 | `FactReviewRequest → RunResponse` |
| `GET /runs/{run_id}/review-results` | Reviewer | 200 | `ReviewResultsResponse` |
| `GET /runs/{run_id}/report` | Reviewer；确认后 RM | 200 | `ReportResponse` |
| `POST /runs/{run_id}/report-review` | Reviewer | 200 | `ReportReviewRequest → RunResponse` |
| `GET /runs/{run_id}/report/export?format=markdown` | Reviewer；确认后 RM | 200 | `text/markdown` 下载 |

`POST /runs/{run_id}/retry` 请求为 `{expected_status: "PAUSED_RETRYABLE"}`。创建 Run、重试和两个人工决策接口必须在相同幂等键下返回第一次的同一业务结果，不重复创建 Run、任务、快照或决策。

## 5. 查询与人工请求 Schema

`FactReviewView` 包含 Run、当前 FACT/CONFLICT 快照版本、字段候选、每个候选的证据定位、冲突差异和允许动作。

```json
{
  "expected_snapshot_version": 1,
  "decisions": [{
    "conflict_id": "uuid",
    "action": "SELECT_SOURCE",
    "selected_evidence_id": "uuid",
    "corrected_value": null,
    "reason": "以 Reviewer 核对的尽调材料为准"
  }]
}
```

HITL-1 动作为 `SELECT_SOURCE | CORRECT_VALUE | REQUEST_RESUBMISSION`。`CORRECT_VALUE` 必须提供类型正确的值与非空原因；`REQUEST_RESUBMISSION` 必须提供原因并使当前 Run 进入 `RETURNED`。版本过期返回 409，整个请求不产生部分写入。

`ReviewResultsResponse` 至少包含 `summary_outcome`、FACT 快照版本、财务指标、规则结果、风险、检索/证据引用、工具状态和 `unsupported_claims`。汇总结论按 SPEC-002 的优先级计算。

报告请求：

```text
ReportReviewRequest
  expected_snapshot_version: integer
  action: CONFIRM_DRAFT | RETURN_FOR_RERUN
  reason: string?  # 退回时必填
```

仅当 `summary_outcome != REVIEW_BLOCKED` 且报告无进入正式结论的 `UNSUPPORTED` 内容时允许 `CONFIRM_DRAFT`，成功后 Run 为 `COMPLETED`；否则返回 409 `REPORT_NOT_CONFIRMABLE` 且不写入决策。`RETURN_FOR_RERUN` 使 Run `RETURNED`，后续由 RM 创建新 Run。确认仅表示 AI 辅助草稿已复核，不表示授信审批通过。

## 6. Problem Details

```json
{
  "type": "https://creditguard.local/problems/stale-snapshot",
  "title": "Snapshot version conflict",
  "status": 409,
  "detail": "The review was based on an outdated fact snapshot.",
  "instance": "/api/v1/runs/{run_id}/fact-review",
  "code": "STALE_SNAPSHOT",
  "trace_id": "uuid"
}
```

固定错误码至少包含：`UNAUTHORIZED`、`FORBIDDEN`、`INVALID_FILE_TYPE`、`FILE_TOO_LARGE`、`CASE_FILE_LIMIT`、`ENCRYPTED_PDF`、`ZIP_LIMIT_EXCEEDED`、`STALE_CASE_VERSION`、`STALE_SNAPSHOT`、`INVALID_STATE_TRANSITION`、`RUN_NOT_RETRYABLE`、`REPORT_NOT_CONFIRMABLE`、`EXTERNAL_SERVICE_UNAVAILABLE`。

## 7. 状态机

```text
DocumentStatus = UPLOADED | PARSING | PARSED | NEEDS_REVIEW | REJECTED
RunStatus      = QUEUED | RUNNING | WAITING_FACT_REVIEW |
                 WAITING_REPORT_REVIEW | PAUSED_RETRYABLE |
                 COMPLETED | RETURNED | FAILED_FINAL
JobStatus      = PENDING | LEASED | RETRYABLE | SUCCEEDED | FAILED_FINAL
RuleOutcome    = PASS | WARN | FAIL | NEEDS_REVIEW
ReportStatus   = DRAFT | AWAITING_REVIEW | CONFIRMED | RETURNED
```

Run 只允许：

```text
QUEUED → RUNNING
RUNNING → WAITING_FACT_REVIEW | WAITING_REPORT_REVIEW | PAUSED_RETRYABLE | FAILED_FINAL
WAITING_FACT_REVIEW → RUNNING | RETURNED
WAITING_REPORT_REVIEW → COMPLETED | RETURNED
PAUSED_RETRYABLE → QUEUED
COMPLETED | RETURNED | FAILED_FINAL 为终态
```

Job 只允许 `PENDING/RETRYABLE → LEASED → SUCCEEDED`；租约过期或外部可重试操作耗尽且未达任务尝试上限时 `LEASED → RETRYABLE`，同时 Run 进入 `PAUSED_RETRYABLE`；人工重试把 Run 改为 `QUEUED` 并重新领取同一任务。不可重试或达到任务尝试上限时 Job 与 Run 均进入 `FAILED_FINAL`。Report 只允许 `DRAFT → AWAITING_REVIEW → CONFIRMED/RETURNED`。状态只能由命名动作触发，不提供通用 PATCH。

Run 进度严格采用 SPEC-003 第 3.3 节映射；等待或暂停时保留最近值，终态 `RETURNED/FAILED_FINAL` 不强制改为 100。

## 8. 业务数据与约束

| 表 | 关键字段 |
|---|---|
| `credit_cases` | id、case_no、customer_name、customer_key、review_date、version、timestamps |
| `documents` | id、case_id、type、version、active、replaces_document_id、storage_key、content_hash、mime、status |
| `review_runs` | id、case_id、status、stage、progress、input_manifest_hash、版本集合 |
| `task_jobs` | id、run_id、status、owner、leased_until、attempt、idempotency_key |
| `snapshots` | id、run_id、kind、version、payload_json、payload_hash |
| `human_decisions` | id、run_id、gate、action、before/after_version、reason、actor |
| `invocations` | id、run_id、provider、operation、requested_model、returned_model、prompt/schema hash、usage、latency、status |
| `audit_events` | id、case_id、run_id、event_type、actor、metadata、created_at |
| `policy_documents/chunks` | 制度包、source hash、chunk ID、定位与 text hash |

至少建立以下唯一约束：`(case_id, document_type, version)`、`(run_id, kind, version)`、`(scope, idempotency_key)`、`(run_id, node_name, input_hash)`。同案件同类型仅一个版本可 `active=true`，替换通过事务将旧版本停用并创建新版本；历史版本不删除。

完整原文、上传物、索引和 Markdown 报告存本地文件系统；数据库只保存随机 `storage_key`、Hash 和元数据，不保存本机绝对路径。

## 9. 快照与证据

`snapshot.kind = PARSE | FACT | CONFLICT | RETRIEVAL | TOOL | RULE | RISK | REPORT`。快照写入后不可更新，人工修订创建新 FACT 快照。

```json
{
  "schema_version": "1.0",
  "run_id": "uuid",
  "kind": "FACT",
  "version": 2,
  "producer": {"type": "workflow_node", "version": "poc-1.0.0"},
  "input_refs": ["snapshot-id"],
  "payload": {},
  "payload_hash": "sha256"
}
```

证据必须解析到材料版本及 PDF 页/块、DOCX 标题路径/段落或 XLSX 工作表/单元格。引用包含 `quote_hash`，报告和规则结果必须能够反查当前 Run 的有效证据。

## 10. LangGraph State、Interrupt 与恢复

```python
class CreditReviewState(TypedDict):
    case_id: str
    run_id: str
    thread_id: str
    trace_id: str
    workflow_version: str
    rule_pack_version: str
    policy_pack_version: str
    policy_index_version: str
    prompt_versions: dict[str, str]
    model_profile: dict[str, str]
    stage: str
    document_version_ids: list[str]
    snapshot_refs: dict[str, str]
    conflict_ids: list[str]
    pending_review: dict[str, object] | None
    decision_refs: list[str]
    retry_count: int
    error_code: str | None
    pause_reason: str | None
```

`thread_id == run_id`；State 只保存引用，不保存原文、完整模型响应、报告正文或密钥。

Interrupt payload 必须可 JSON 序列化，包含 `gate`、`run_id`、`expected_snapshot_version`、冲突或报告引用及允许动作。API 验证决策和版本后，以唯一键原子写入一次 `human_decision`，再用同一 `thread_id` 执行 `Command(resume=decision)`。节点恢复会从节点起点重跑，因此 interrupt 之前的副作用必须幂等。

## 11. 规则、工具、RAG 与报告契约

规则包为不可变 YAML；同一版本出现不同 Hash 时启动失败。白名单操作符和十条规则边界以 SPEC-002 为准，财务公式引用预注册函数 ID，不接受代码字符串。

工具固定为：

```text
get_customer_profile(customer_key) → industry_status, risk_status, as_of, source
get_credit_exposure(customer_key) → approved_amount, used_amount, available_amount, currency, as_of
check_blacklist(customer_key) → matched, list_type, as_of, source
```

输入输出由 Pydantic 校验，只读且限定当前 Run；失败使相关规则 `NEEDS_REVIEW`，不得生成合规结论。

每条 RetrievalHit 保存 query/rule/chunk ID、制度版本、定位、BM25/Dense 排名分数、RRF 分数、rerank 排名分数、selected 和索引清单 Hash。排名从 1 开始；融合和同分排序遵循 SPEC-003。

每个风险包含 `HIGH|MEDIUM|LOW`、解释、证据引用和 `SUPPORTED|UNSUPPORTED`。`UNSUPPORTED` 不进入正式结论。模型调用元数据至少记录请求别名、服务返回模型、区域、Prompt Hash、Schema Hash、时间、用量和状态。

## 12. 验收标准

- AC-004-01：OpenAPI 可生成 TypeScript 类型，CI 检测漂移。
- AC-004-02：异步接口、Schema、成功码、分页、进度和状态转换均符合本契约。
- AC-004-03：重复幂等请求不创建重复 Run、任务、快照或决策。
- AC-004-04：过期人工决策返回 409 且无部分写入。
- AC-004-05：State 和 API 响应不含密钥、完整模型响应或本机路径。
- AC-004-06：每个事实、规则和风险均能解析到当前 Run 的有效证据。
