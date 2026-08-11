# 授信智能合规审查平台 GitHub 发布与完整演示规范 V1.0

**编号：SPEC-006**  
**版本：V1.0**  
**状态：IMPLEMENTING**
**评审基线：d402422**  
**目标发布：v0.1.0 PoC**

---

## 1. 文档目标与评审门禁

本文档定义 CreditGuard AI PoC 的 GitHub 公开发布、完整网页演示、演示数据、公开文档、CI、分支保护和 Release 验收标准。

本规范进入 APPROVED 前，只允许维护本规范、索引和 PLANNED 测试样例，不得开始 Demo API、前端页面、演示素材、远端仓库或 Release 实现。评审通过后状态依次为：

~~~text
REVIEWING → APPROVED → IMPLEMENTING → VERIFIED → DONE
~~~

实现必须保留现有根提交 d402422 及后续历史，不得重写或压缩初始提交。

## 2. 与既有规范的关系

- [SPEC-000](./SPEC-000-project-governance.md) 继续约束 Spec-first、测试积累和 Definition of Done。
- [SPEC-002](./SPEC-002-credit-review-poc-scope-v1.md) 定义角色、正常/高风险案件、规则和 PoC 非范围。
- [SPEC-003](./SPEC-003-credit-review-architecture-poc-v1.md) 定义单机架构、LangGraph、RAG、Worker 与安全边界。
- [SPEC-004](./SPEC-004-credit-review-contracts-poc-v1.md) 继续作为核心 REST API 和数据契约来源。
- [SPEC-005](./SPEC-005-credit-review-evaluation-poc-v1.md) 继续定义离线评测和质量硬门槛。

SPEC-006 只补充公开交付、演示专用能力和 GitHub 治理，不扩大为生产授信系统。

## 3. 发布目标与成功定义

目标仓库为当前 GitHub CLI 已认证个人账户下的公开仓库 creditguard-ai，许可证为 Apache-2.0，首个标签和 GitHub Release 为 v0.1.0。

发布成功必须同时满足：

1. 新用户可在 Windows 按 README 一键启动 API、Worker 和 Web。
2. 用户可在网页中完整走通 RM 和 Reviewer 两种角色。
3. 正常案件和高风险期限冲突案件可使用纯合成材料复现。
4. README、架构文档、演示指南、截图、GIF 和脱敏验收报告可公开查看。
5. GitHub Actions 的 backend、frontend、e2e 检查全部通过。
6. main 禁止强推和删除，并要求三个状态检查通过。
7. 仓库、Release、文档和媒体中不存在密钥、真实客户数据、原始外部响应或本机绝对路径。

## 4. 范围与非范围

### 4.1 本期范围

- 完整 RM/Reviewer 网页工作台。
- 一键加载正常和高风险演示场景。
- 手工创建案件、上传材料和启动审查。
- 事实冲突裁定、规则/风险/证据查看、报告复核和 Markdown 导出。
- Vue Router、组合式 API、OpenAPI 生成类型。
- Playwright Chromium E2E。
- README、架构、演示、验收和社区治理文档。
- 四张 PNG 与一张短 GIF。
- 公开 GitHub 仓库、CI、分支保护、v0.1.0 标签和 Release。

### 4.2 明确不做

- 在线公共演示环境或长期托管后端。
- Linux CI 矩阵、Docker、Kubernetes 或云资源。
- 生产认证、真实银行系统、真实客户数据或自动授信审批。
- GitHub Pages 静态 Mock。
- 自动上传或复用本机 DashScope/MinerU 密钥。
- 在普通 push、PR 或 fork 中访问真实外部 API。

## 5. 演示角色与页面

### 5.1 角色

- RM：创建案件、上传材料、启动 Run、查看进度、补件问题和已确认报告。
- Reviewer：查看完整事实、冲突、规则、风险、制度证据和报告草稿，执行 HITL-1 与 HITL-2。

角色仍使用 demo-rm 和 demo-reviewer，由后端执行权限校验；前端隐藏按钮不能替代后端 RBAC。

### 5.2 固定路由

| 路由 | 主要能力 |
|---|---|
| / | 案件总览、角色切换、正常/高风险一键演示入口 |
| /cases/new | RM 创建案件和手工上传材料 |
| /cases/:caseId | 材料版本、Run 列表、进度和可执行动作 |
| /runs/:runId/facts | Reviewer 查看候选、证据和冲突并执行 HITL-1 |
| /runs/:runId/results | 事实、财务指标、R01～R10、风险、制度证据和工具状态 |
| /runs/:runId/report | Reviewer 确认/退回报告，RM 查看已确认报告和导出 |

前端每 2 秒轮询活动 Run；进入人工等待、可重试暂停、失败、完成或退回状态后停止。请求失败使用统一 Problem Details 显示可理解错误，不显示堆栈、密钥或原始模型响应。

## 6. 固定演示场景与材料

### 6.1 DEMO-NORMAL-001

- 申请期限和尽调期限均为 24 个月。
- 行业允许、非黑名单、风险状态 NORMAL。
- 申请金额不超过可用额度。
- 资产负债率不超过 70%，流动比率不低于 1.0。
- 事实阶段不触发 HITL-1。
- R01～R10 全部 PASS，所有案件仍强制进入 HITL-2。

### 6.2 DEMO-HIGH-001

- 授信申请书期限为 24 个月。
- 尽职调查报告期限为 48 个月。
- Reviewer 必须在 HITL-1 选择尽调报告的 48 个月并填写非空原因。
- 其余准入、额度、财务和工具结果均满足要求。
- 恢复执行后 R07 必须 FAIL，summary_outcome 必须为 NON_COMPLIANT。
- 报告仍进入强制 HITL-2，确认只代表草稿已复核。

### 6.3 材料包

每个场景固定包含：

| 材料 | 格式 | 主要内容 |
|---|---|---|
| 营业执照 | 文本 PDF | 企业名称、统一社会信用代码、成立日期、行业 |
| 授信申请书 | DOCX | 申请金额、币种、期限、用途 |
| 尽职调查报告 | 文本 PDF | 企业信息、期限、用途和风险说明 |
| 财务报表 | XLSX | 总资产、总负债、流动资产、流动负债 |

材料目录携带 manifest.json 和 SHA256。全部企业、证件号、金额和制度均为合成数据，并在文件内显著标注“仅用于演示”。

## 7. 受控 Demo API 契约

仅当 CREDIT_REVIEW_DEMO_MODE=true 时注册：

~~~text
POST /api/v1/demo/scenarios/{scenario_id}
~~~

### 7.1 输入

- scenario_id 只能为 DEMO-NORMAL-001 或 DEMO-HIGH-001。
- Header X-Demo-User-Id 必须为 demo-rm。
- Header Idempotency-Key 必填。
- 无请求体，不接收本机路径、URL、文件内容、SQL 或扩展参数。

### 7.2 输出

DemoScenarioResponse：

~~~json
{
  "scenario_id": "DEMO-NORMAL-001",
  "case_id": "uuid",
  "run_id": "uuid",
  "case_version": 1,
  "input_document_version_ids": ["uuid"],
  "run_status": "QUEUED",
  "created": true
}
~~~

- 首次成功返回 201，created=true。
- 相同 Idempotency-Key 和相同场景重放返回 200、相同 case_id/run_id，created=false。
- 相同 Idempotency-Key 携带不同场景返回 409 IDEMPOTENCY_CONFLICT。
- 未知场景返回 404 DEMO_SCENARIO_NOT_FOUND。
- 非 RM 返回 403 FORBIDDEN。
- 缺少幂等键返回 400 IDEMPOTENCY_KEY_REQUIRED。
- 清单或 Hash 不一致返回 500 DEMO_FIXTURE_INVALID，且不得产生部分案件、材料或 Run。
- Demo 模式关闭时路由不注册，统一返回 404。

创建流程必须复用正式案件、上传校验、材料版本和 Run 服务，并在单次失败时回滚业务记录和演示文件副作用；不得直接写入伪造事实、规则、风险或报告结果。

dev.ps1 为本地演示设置 CREDIT_REVIEW_DEMO_MODE=true；直接启动 API 时默认 false。

## 8. 前端实现约束

- 使用 Vue 3、TypeScript、Element Plus、Vue Router 和组合式 API，不引入 Pinia。
- FastAPI OpenAPI 是接口单一来源；生成并跟踪 TypeScript 类型，CI 重生成后执行漂移检查。
- 所有写操作携带幂等键和预期版本。
- Reviewer 裁定必须显示两个来源、规范值、材料版本和证据定位。
- 规则结果显示 PASS/WARN/FAIL/NEEDS_REVIEW，R07 FAIL 必须突出但不得展示为最终授信拒绝。
- 制度引用可定位到制度、版本、条款/chunk 和引用文本。
- 报告 Markdown 禁止原始 HTML，并在渲染前后清洗；恶意标签、事件属性和 javascript URL 不得进入 DOM。
- RM 不得查看未确认报告；Reviewer 操作由后端再次校验。

## 9. README、文档与演示媒体

README 至少包含：

1. 项目定位、业务问题、PoC 边界和合成数据声明。
2. CI、Python、License 和 PoC 状态徽章。
3. 演示 GIF 与关键截图。
4. Mermaid 总体架构和 LangGraph/HITL 流程。
5. 技术栈、目录结构和关键设计。
6. 一键启动、环境变量、手工上传和两条演示步骤。
7. API、文档解析、RAG、规则、工具、安全和评测摘要。
8. 脱敏验收结果、限制、路线图、英文摘要和许可证。

新增：

- docs/architecture.md
- docs/demo-guide.md
- docs/acceptance/poc-v0.1.0.md
- CONTRIBUTING.md
- SECURITY.md
- CODE_OF_CONDUCT.md
- CHANGELOG.md
- .github/ISSUE_TEMPLATE/
- .github/PULL_REQUEST_TEMPLATE.md

固定媒体：

- docs/assets/dashboard.png
- docs/assets/material-run.png
- docs/assets/fact-review.png
- docs/assets/report-review.png
- docs/assets/creditguard-demo.gif

PNG 使用一致的 1280×720 或 1440×900 视口。GIF 展示“加载高风险场景→Reviewer裁定48个月→R07 FAIL→报告复核”，不超过 8MB。媒体只能出现合成数据，不得出现浏览器个人资料、密钥、请求ID、本机路径或终端窗口。

## 10. 公开验收证据

artifacts/ 继续被 Git 忽略。公开报告只整理以下脱敏信息：

- 20 个离线案件与 2 个演示案件。
- 规则一致率、Recall@5、MRR、NDCG 和 failure_count。
- 后端、前端、Playwright、安全、契约和构建状态。
- DashScope embedding/reranker 与 MinerU 冒烟的 PASS/FAIL、模型名、结果形状和时延范围。
- SPEC-001 Hash 未变化结论。

禁止写入 API Key、Authorization、Provider请求ID、原始响应、原始Markdown/ZIP、本机绝对路径或真实客户信息。

## 11. GitHub 仓库与 Release

- 仓库：当前 gh auth 账户下的公开 creditguard-ai。
- 描述：Spec-first AI credit compliance review PoC with LangGraph, RAG, rules and human-in-the-loop.
- Topics：llm、rag、langgraph、fastapi、vue3、credit-risk、compliance、human-in-the-loop。
- 默认分支：main。
- 保留 Apache-2.0 LICENSE 和 NOTICE。
- main 禁止 force push 和删除。
- main 要求 backend、frontend、e2e 状态检查通过，不强制他人审批。
- 标签 v0.1.0 必须指向最终绿色 main 提交。
- GitHub Release 标题为 CreditGuard AI PoC v0.1.0，附 CHANGELOG、脱敏验收报告和合成演示材料包。

普通 CI 不配置现有 DashScope/MinerU 密钥。手动外部冒烟 Workflow 保留，但首次发布不要求设置 GitHub Secrets。

## 12. CI 契约

Windows GitHub Actions 固定包含：

- backend：uv 锁定安装、Ruff、Pyright、Pytest、Alembic、离线评测、安全扫描和 OpenAPI 检查。
- frontend：npm ci、类型检查、Vitest、OpenAPI TypeScript 漂移和生产构建。
- e2e：启动本地确定性 API、Worker、Web，启用 Demo 模式并运行 Playwright Chromium。

E2E 失败时上传截图、Trace 和视频 Artifact；成功时不长期保存运行时数据库、上传材料、日志或原始报告。所有 Workflow 默认 permissions.contents=read；只有创建 Release 的显式步骤可申请 contents=write。

## 13. 发布顺序与回滚

1. SPEC-006 APPROVED 后创建 feat/github-release-v0.1.0。
2. 完成实现并在本地通过全部门槛。
3. 合并到 main，保留 d402422 及完整历史。
4. 创建公开仓库并推送 main。
5. 等待 GitHub Actions 全绿后设置分支保护。
6. 创建 v0.1.0 标签和 GitHub Release。
7. 更新本规范至 VERIFIED；文档、链接和 Release 再次核对后进入 DONE。

如果公开前发现密钥、PII、错误演示结论或不可复现构建，禁止创建标签和 Release。若公开后发现上述问题，先下架 Release 和受影响资产、轮换可能泄露的凭据，再通过新提交修复；不得重写已公开 Git 历史来掩盖问题。

## 14. Acceptance Criteria

- AC-006-01：SPEC-006、索引和测试样例已评审并进入 APPROVED 后才开始实现。
- AC-006-02：两组合成材料可由本地解析器处理并产生可追溯证据。
- AC-006-03：Demo API 只在 Demo 模式注册，只接受两个固定场景且幂等。
- AC-006-04：正常案件完整网页路径通过并强制进入 HITL-2。
- AC-006-05：高风险案件完成 HITL-1 后 R07=FAIL、summary_outcome=NON_COMPLIANT。
- AC-006-06：RM 手工创建、上传、启动、查看已确认报告路径通过。
- AC-006-07：OpenAPI 生成 TypeScript 类型无漂移，核心 REST 契约无非兼容变更。
- AC-006-08：报告 Markdown 清洗、RBAC 和 Demo 接口安全边界通过。
- AC-006-09：README、文档、PNG、GIF、相对链接和合成数据声明完整。
- AC-006-10：backend、frontend、e2e GitHub Actions 全部通过。
- AC-006-11：公开仓库无密钥、真实数据、原始外部响应和本机路径。
- AC-006-12：main 分支保护生效，v0.1.0 指向最终绿色提交且 Release 资产可下载。

## 15. Acceptance Criteria → Test Case

| Acceptance Criteria | Test Case ID |
|---|---|
| AC-006-01 | TC-WF-029、TC-WF-030 |
| AC-006-02 | TC-DOC-014 |
| AC-006-03 | TC-WF-024、TC-SEC-018、TC-SEC-019 |
| AC-006-04 | TC-WF-025 |
| AC-006-05 | TC-WF-026 |
| AC-006-06 | TC-WF-027 |
| AC-006-07 | TC-WF-028 |
| AC-006-08 | TC-SEC-018、TC-SEC-019、TC-SEC-020 |
| AC-006-09 | TC-WF-029、TC-SEC-021 |
| AC-006-10 | TC-WF-030、TC-SEC-022 |
| AC-006-11 | TC-SEC-021、TC-SEC-022 |
| AC-006-12 | TC-WF-030 |

## 16. Definition of Done

~~~text
□ SPEC-006 已 APPROVED
□ 两条一键演示和手工上传路径已实现
□ 正常、高风险及安全边界测试已通过
□ README、架构、演示、社区和验收文档已完成
□ 截图和GIF只包含合成数据
□ 本地质量门槛和GitHub Actions全部通过
□ main分支保护已生效
□ v0.1.0标签与Release已创建
□ 测试结果、证据和Spec状态已同步
□ 未解决问题和剩余风险已披露
~~~
