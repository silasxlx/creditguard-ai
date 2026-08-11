# 授信智能合规审查平台 PoC 技术架构 V1.0

**编号：SPEC-003**  
**版本：V1.0**  
**状态：APPROVED**  
**评审结论：2026-08-10 用户评审通过**  
**业务范围：[SPEC-002](./SPEC-002-credit-review-poc-scope-v1.md)**  
**接口契约：[SPEC-004](./SPEC-004-credit-review-contracts-poc-v1.md)**

---

## 1. 架构目标与阶段边界

在 Windows 单机环境中构建可恢复、可审计、可评测的授信审查纵向薄切片。架构优先保证事实与证据可追溯、确定性逻辑可复现、人工关口不可绕过。PoC 不引入 Redis、Celery、Milvus、PostgreSQL、MinIO、PaddleOCR、MCP、Docker Compose 或自治 Multi-Agent。

```text
Vue 3 工作台
  → FastAPI /api/v1
  → SQLite 业务库与任务租约
  → 独立 Worker
  → LangGraph + 独立 SQLite Checkpoint
  → 解析/抽取/冲突/HITL-1/RAG/工具/规则/风险/报告/HITL-2
```

## 2. 技术基线

| 层 | 选型 |
|---|---|
| 后端 | Python 3.13、uv、FastAPI、Pydantic、SQLAlchemy 2、Alembic |
| 工作流 | LangGraph、`langgraph-checkpoint-sqlite` |
| 前端 | Vue 3、TypeScript、Element Plus、npm |
| 文档 | PyMuPDF、python-docx、openpyxl、MinerU API 兜底 |
| RAG | jieba、BM25、FAISS `IndexFlatIP`、DashScope embedding/rerank |
| 模型 | `qwen3.7-flash`、`text-embedding-v4`、`qwen3-rerank`，DashScope 北京端点 |
| 质量 | Ruff、Pyright、Pytest、ESLint、Vue 类型检查、Vitest、Playwright Chromium |

`langgraph-checkpoint-sqlite` 作为显式依赖锁定，不依赖 LangGraph 的传递依赖碰巧安装。

## 3. 前端、API 与 Worker 边界

前端提供案件、材料、进度、事实复核、审查结果、报告复核和 Markdown 导出视图，每 2 秒查询 Run。页面只渲染纯文本或经白名单清洗的 Markdown，禁止直接渲染未经清洗的模型 HTML。

FastAPI 只处理文件接收、校验、短事务、任务提交、状态查询和人工决策。解析、模型、RAG、规则和报告均由 Worker 执行。PoC 启动一个 Worker，但租约协议支持进程异常恢复。

### 3.1 任务租约固定参数

- Worker 每 2 秒轮询一次，每次最多领取 1 个任务。
- 租约 TTL 为 60 秒；领取后每 20 秒续租。
- 任务级最多执行 3 次。租约过期且 `attempt < 3` 时回到 `RETRYABLE`；达到 3 次进入 `FAILED_FINAL`。
- 同一任务的写入幂等键为 `run_id + node_name + input_snapshot_hash`，数据库唯一约束阻止重复有效结果。
- Worker 重启后使用同一 `thread_id` 从最近安全 Checkpoint 恢复，不新建 Run。

### 3.2 外部调用固定参数

- 每个外部操作总计最多 3 次尝试，退避 1、2、4 秒，并增加 0–250ms 随机抖动。
- 可重试：网络超时、HTTP 429、HTTP 5xx、临时连接失败。
- 不可重试：认证/授权失败、无效请求、格式不支持、Schema 或本地配置错误。
- DashScope：连接超时 10 秒、读取超时 60 秒、单次总超时 90 秒。
- MinerU：提交超时 30 秒、轮询间隔 2 秒、单文档最长等待 180 秒。
- 3 次仍失败时保存 Checkpoint 并进入 `PAUSED_RETRYABLE`；不可重试错误或任务级达到 3 次时进入 `FAILED_FINAL`。

### 3.3 进度映射

进度仅代表工作流阶段，不代表授信审批结果：`load_run=2`、`parse_documents=20`、`extract_facts=35`、`normalize_validate=45`、`detect_conflicts=50`、`retrieve_policies=65`、`tools_metrics_rules=80`、`synthesize_validate_risks=88`、`render_report=95`、`COMPLETED=100`。等待人工或可重试暂停时保持最近已完成阶段的数值。

## 4. 文档解析与事实抽取

### 4.1 本地解析

- PDF：拒绝加密文件；PyMuPDF 提取页、块、文本与坐标。
- DOCX：按标题、段落和表格单元格形成块，记录标题路径与段落序号。
- XLSX：读取工作表、单元格地址、显示值和公式缓存值；缓存缺失进入 `NEEDS_REVIEW`。

有效字符是移除空白与控制字符后的字符。满足任一条件时调用 MinerU：无文本、平均每页有效字符少于 50、本地解析异常、`可定位字符数 / 已抽取字符数 < 0.90`。调用时必须记录触发原因。

### 4.2 MinerU 适配器契约

```text
submit(document_version_id, content_hash) -> provider_task_id
get_status(provider_task_id) -> PENDING | RUNNING | SUCCEEDED | FAILED
fetch_result(provider_task_id) -> MineruResult
```

PoC 只依赖 MinerU 稳定输出 `content_list.json`，不依赖仍可能变化的 `content_list_v2.json`。结果统一转换为 `ParsedBlock`：

```text
block_id = sha256(document_version_id | page | reading_order | text_hash)
page = page_idx + 1
bbox = 0..1000 归一化坐标
type = text | title | table | image | equation | other
content = text 或经过清洗的表格 HTML
section_path、reading_order、provider_backend、provider_version
```

`provider_task_id`、后端、版本、结果 Hash 和失败原因写入 invocation/解析快照。相同 `document_version_id + content_hash` 的重试复用远端任务，避免重复提交。

### 4.3 LLM 结构化抽取

外部抽取最多 2 路并发，必须按版本化 Prompt 和 Pydantic JSON Schema 输出。JSON 解析或 Schema 校验失败属于可重试错误，总计 3 次；重试保持输入、Prompt Hash 和 Schema Hash 不变。3 次仍失败时 Run 进入 `PAUSED_RETRYABLE`。程序负责日期、金额、币种、期限、百分比归一化和证据反查；不使用模型自报置信度作为事实可信度。

## 5. 冲突检测与 HITL-1

离散字段与期限精确比较；金额和财务值使用 [SPEC-002](./SPEC-002-credit-review-poc-scope-v1.md) 约定的绝对与相对差异公式。所有候选保留原始值、规范值、材料版本及证据定位。检测器只生成冲突，不自动选择权威来源。缺件、实质冲突或事实不可用时进入 HITL-1。

## 6. RAG 可复现设计

### 6.1 切分与标识

5 份合成制度 PDF 按章、节、条、款、列表、语句和表格边界切分并携带父标题路径。单块最多 600 个中文字符；超长条款按自然边界拆分并保留约 80 字重叠；拆表重复表头。

```text
chunk_id = sha256(policy_document_id | source_hash | section_path | ordinal | text_hash)
```

### 6.2 分词、索引与清单

- Unicode NFKC 归一，拉丁字符转小写，使用 `jieba.cut_for_search`。
- 金融词典固定为 `config/rag/finance_terms.txt`；停用词固定为 `config/rag/stopwords.txt`。
- 两个文件及分词配置均计算 Hash 并进入索引清单。
- Dense 使用 `text-embedding-v4`、1024 维、L2 归一化；FAISS 使用 `IndexFlatIP`。
- 索引清单记录 embedding 请求模型和服务返回模型、维度、归一化开关、policy pack Hash、词典/停用词/分词器 Hash、有序 chunk ID 列表和构建器版本。
- 运行时任一清单项不一致必须重建；无法重建则启动失败，禁止静默使用旧索引。

### 6.3 检索、融合与重排

规则版本化模板生成 Query，不允许 LLM 自由扩展多 Query。BM25 与 Dense 各取 Top 30，排名从 1 开始：

```text
RRF(d) = Σ 1 / (60 + rank_i(d))
```

按 chunk_id 去重并取 Top 20。RRF 同分时依次按最佳单路排名升序、`chunk_id` 升序。`qwen3-rerank` 重排后保留 Top 5；重排分数相同按 `chunk_id` 升序。首版不设硬分数阈值。每阶段候选、排名、分数、版本及索引清单 Hash 全部保存。

## 7. 规则、财务与只读工具

规则包采用不可变 YAML，只允许 `eq/ne/gt/gte/lt/lte/in/not_in/is_present`、显式 AND/OR 和预注册函数，禁止 `eval`、动态导入和任意表达式。财务公式使用 Decimal，边界与异常结果以 SPEC-002 为准。

只读工具为 `get_customer_profile`、`get_credit_exposure`、`check_blacklist`。工作流按规则映射确定性调用；LLM 只能读取结果进行解释，不能选择工具、修改参数来源、生成 SQL、调用 Shell 或访问任意 URL。

## 8. 为什么使用 LangGraph

PoC 需要显式条件分支、长耗时外部调用、两个人工中断点、进程重启恢复和失败续跑。LangGraph 用于状态机与持久化，不用于构建自治 Agent 群。`thread_id == run_id`，每次 Run 固定工作流版本。

```text
load_run → parse_documents → extract_facts → normalize_validate_facts
→ detect_conflicts → [conditional interrupt_fact_review]
→ retrieve_policies → call_readonly_tools → calculate_financial_metrics
→ execute_rules → synthesize_risks → validate_evidence
→ render_report_draft → [mandatory interrupt_report_review] → finalize_report
```

LangGraph 恢复中，被中断节点会从节点起点重新执行，而不是从 `interrupt()` 后一行继续。因此所有 interrupt 之前的写入必须幂等，人工决策先以唯一键写入一次，再使用同一 `thread_id` 和 `Command(resume=decision)` 恢复。

## 9. State 与持久化

State 仅保存 case/run/thread/trace ID、工作流/规则/制度/索引/Prompt/模型版本、当前阶段、材料版本 ID、快照引用、冲突/人工决策引用、重试计数、错误分类和暂停原因。文档全文、完整解析内容、完整模型响应、报告正文和密钥不进入 Checkpoint。

业务库与 LangGraph Checkpoint 使用两个 SQLite 文件：前者由 SQLAlchemy/Alembic 管理，后者由 LangGraph 管理。两库不得互相建表或跨库事务；业务快照是审计事实，Checkpoint 是恢复状态。

## 10. 报告、安全与审计

固定模板填充事实、规则、指标、证据、工具状态和人工记录。LLM 只生成摘要与风险解释；证据校验失败的内容标记 `UNSUPPORTED` 并从正式结论剔除。

上传安全限制：单文件 20MB；Office ZIP 条目数不超过 5000、展开总大小不超过 100MB、任一条目压缩比不超过 100:1。超限在解析前拒绝。服务端使用随机存储名，校验扩展名、MIME、文件头、宏、加密、路径穿越和案件活动材料数量。

审计记录关键读写、材料/规则/制度/Prompt/模型版本、人工决策、工具与模型调用元数据、重试和导出，不记录密钥或完整外部响应。`.env`、数据库、索引、日志、上传物、真实 API 响应和本机路径禁止提交。

## 11. 本地运行与 CI

提供 `dev.ps1` 一键启动 API、Worker、Web，同时保留三个独立命令。Windows GitHub Actions 执行后端格式/类型/测试、前端 lint/类型/组件测试、OpenAPI 类型漂移和 Playwright Mock E2E。PR 与 fork 不调用真实外部 API；真实 DashScope/MinerU 冒烟仅由手动 workflow 读取 GitHub Secrets 执行。

## 12. 架构验收标准

- AC-003-01：API 提交后立即返回 Run，长任务只由 Worker 执行。
- AC-003-02：租约过期可按固定参数重新领取且不产生重复有效结果。
- AC-003-03：两道 HITL 可中断并在进程重启后使用同一 thread 恢复。
- AC-003-04：解析质量不足时按确定性阈值触发 MinerU，并可还原定位与调用版本。
- AC-003-05：RAG 候选、分词、索引、排名、融合、重排和引用可复现。
- AC-003-06：LLM 不能选择工具，规则引擎不能执行任意代码。
- AC-003-07：外部调用按固定超时和退避重试，达到边界后进入明确暂停或终态。
- AC-003-08：业务库与 Checkpoint 库相互独立。
