# Workflow 测试样例

## SPEC-001 基线引用

| Test Case ID | 名称 | 来源 |
|---|---|---|
| `TC-WF-001` | Happy Path | SPEC-001 第 48 节 |
| `TC-WF-002` | High Risk | SPEC-001 第 48 节 |

## TC-WF-003 Spec 审批门禁

- 关联 Spec / FR / User Story：SPEC-000 第 2、3、9 节
- 测试目标：验证未进入 `APPROVED` 的 Spec 不能进入正式开发。
- 前置条件：存在一个状态为 `DRAFT` 或 `REVIEWING` 的功能 Spec。
- 输入数据：一个要求直接开始实现但尚未完成验收标准和测试样例的开发请求。
- 执行步骤：
  1. 读取 Spec 状态。
  2. 检查 Acceptance Criteria 和 Test Case ID。
  3. 尝试进入正式实现阶段。
- 预期结果：实现被阻止；工作停留在 Spec 讨论或评审阶段，并明确缺失内容。
- 异常或边界条件：已明确标记且满足约束的 Spike 可以执行，但不得作为正式实现交付。
- 自动化状态：MANUAL
- 最近执行结果：NOT_RUN
- 证据或日志引用：待首次执行后补充。

## TC-WF-004 测试样例积累门禁

- 关联 Spec / FR / User Story：SPEC-000 第 6、7、10 节
- 测试目标：验证没有新增或更新测试样例的工作不能标记完成。
- 前置条件：存在一项已实现的功能、缺陷修复、规则变更、架构变更或文档变更。
- 输入数据：交付内容及其关联 Spec、Acceptance Criteria 和测试记录。
- 执行步骤：
  1. 检查交付内容是否关联 Test Case ID。
  2. 检查测试是否执行并记录结果。
  3. 检查结果是否包含证据或日志引用。
- 预期结果：缺少任一项时 Definition of Done 不通过；补齐后才允许完成。
- 异常或边界条件：`NOT_APPLICABLE` 必须给出可审查的理由，不能用于规避测试。
- 自动化状态：MANUAL
- 最近执行结果：NOT_RUN
- 证据或日志引用：待首次执行后补充。

## TC-WF-005 Spike 与正式实现隔离

- 关联 Spec / FR / User Story：SPEC-000 第 5 节
- 测试目标：验证探索性代码不会未经 Spec 评审直接成为正式实现。
- 前置条件：存在一个已登记目标、时间盒和输出的 Spike。
- 输入数据：Spike 代码、实验结论和相关 Draft Spec。
- 执行步骤：
  1. 检查 Spike 标记和范围。
  2. 检查是否使用真实敏感数据或生产系统。
  3. 检查实验结论是否回写 Spec。
  4. 尝试把 Spike 直接标记为正式交付。
- 预期结果：直接交付被阻止；必须完成 Spec 评审并按正式实现要求重新验证。
- 异常或边界条件：纯文档调研仍需记录结论，但不要求形成可运行代码。
- 自动化状态：MANUAL
- 最近执行结果：NOT_RUN
- 证据或日志引用：待首次执行后补充。

## TC-WF-006 正常案件端到端

- 关联 Spec / FR / User Story：SPEC-002 第6.1节；AC-002-01
- 测试目标：验证正常案件不触发HITL-1但必须进入HITL-2。
- 前置条件：固定Mock、正常四类材料和制度索引。
- 输入数据：DEMO-NORMAL-001。
- 执行步骤：创建、上传、启动、轮询、Reviewer确认报告。
- 预期结果：Run完成；规则无FAIL/NEEDS_REVIEW；报告可导出且证据完整。
- 异常或边界条件：页面轮询中断后恢复。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-007 高风险期限冲突端到端

- 关联 Spec / FR / User Story：SPEC-002 第6.2节；AC-002-02/03
- 测试目标：验证24/48个月冲突、人工裁定和R07失败闭环。
- 前置条件：高风险合成材料。
- 输入数据：DEMO-HIGH-001。
- 执行步骤：启动Run、在HITL-1选择48个月、继续并确认报告。
- 预期结果：裁定前不形成R07最终结论；裁定后R07=FAIL并引用期限制度。
- 异常或边界条件：Reviewer改为手工修订值。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-008 HITL权限与恢复

- 关联 Spec / FR / User Story：SPEC-002 第4、9节；SPEC-003 第10～12节
- 测试目标：验证两个interrupt可持久化且不能被RM绕过。
- 前置条件：Run分别停在两个gate。
- 输入数据：RM和Reviewer请求、进程重启。
- 执行步骤：RM尝试决策；重启Worker；Reviewer提交正确版本决策。
- 预期结果：RM返回403；重启后仍等待原gate；Reviewer可恢复一次。
- 异常或边界条件：重复提交相同幂等键。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-009 报告退回创建新Run

- 关联 Spec / FR / User Story：SPEC-002 第5节；SPEC-004 第14、15节
- 测试目标：验证RETURN_FOR_RERUN关闭当前发布路径且后续创建新Run。
- 前置条件：Run等待报告复核。
- 输入数据：Reviewer退回原因和RM补件。
- 执行步骤：退回、上传新版本、创建新Run并查询旧Run。
- 预期结果：旧Run/报告不可变；新Run引用新材料并有独立版本链。
- 异常或边界条件：无原因退回。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-010 Worker租约恢复

- 关联 Spec / FR / User Story：SPEC-003 第3.1节；AC-003-02
- 测试目标：验证Worker中断后任务可重新领取且结果不重复。
- 前置条件：可控制租约时钟和Worker生命周期。
- 输入数据：执行到中间节点的任务。
- 执行步骤：以2秒轮询领取任务，终止20秒续租，将时钟推进超过60秒，再启动新Worker。
- 预期结果：新Worker在attempt小于3时领取并用同一thread从checkpoint恢复；仅一份有效节点快照和报告。
- 异常或边界条件：旧Worker过期后恢复写入；第3次租约失败进入FAILED_FINAL。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-011 幂等请求

- 关联 Spec / FR / User Story：SPEC-004 第3、15节；AC-004-03
- 测试目标：验证重复创建Run、重试和人工决策不重复写入。
- 前置条件：固定Idempotency-Key。
- 输入数据：相同请求并发及顺序重复提交。
- 执行步骤：提交两次并查询控制表和快照。
- 预期结果：返回同一业务结果，不产生重复Run、任务、快照或决策。
- 异常或边界条件：同一Key配不同payload。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-012 外部服务失败后续跑

- 关联 Spec / FR / User Story：SPEC-003 第3.2、4.2、8节；SPEC-005 第9节；AC-003-07
- 测试目标：验证3次失败后暂停，重试从安全节点恢复。
- 前置条件：DashScope/MinerU Mock可配置失败次数。
- 输入数据：连续3次失败后恢复正常。
- 执行步骤：模拟三次可重试失败，核对1/2/4秒退避及抖动、确认PAUSED_RETRYABLE，再调用retry。
- 预期结果：保留最近进度；同一thread从安全checkpoint恢复；幂等写入不重复并继续到下一人工关口。
- 异常或边界条件：认证、Schema或不支持格式等不可重试错误直接进入FAILED_FINAL。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-013 过期人工决策

- 关联 Spec / FR / User Story：SPEC-004 第10、15节；AC-004-04
- 测试目标：验证乐观并发控制阻止旧页面覆盖新事实。
- 前置条件：Reviewer页面持有事实v1，后台已产生v2。
- 输入数据：expected_snapshot_version=1的决策。
- 执行步骤：提交决策并检查数据库。
- 预期结果：返回409 STALE_SNAPSHOT，不产生部分决策或新快照。
- 异常或边界条件：刷新后使用v2再次提交。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-014 异步API、进度与状态契约

- 关联 Spec / FR / User Story：SPEC-003 第3节；SPEC-004 第3～7节；AC-003-01/AC-004-02
- 测试目标：验证创建Run立即返回、长任务不在API进程执行，Schema、成功码、进度和状态转换符合契约。
- 前置条件：API和可暂停Worker Mock可用。
- 输入数据：合法案件、四类活动材料、过期case version和非法状态动作。
- 执行步骤：创建Run并测量响应；逐节点推进Worker；查询Run；尝试非法状态转换。
- 预期结果：创建返回202和QUEUED；进度按固定映射递增；等待时保持最近值；非法转换返回Problem Details。
- 异常或边界条件：重复Idempotency-Key、列表分页limit超过100、报告导出格式非法。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-015 业务库与Checkpoint库隔离

- 关联 Spec / FR / User Story：SPEC-003 第9节；AC-003-08
- 测试目标：验证SQLAlchemy业务表和LangGraph checkpoint表位于两个独立SQLite文件并由各自组件管理。
- 前置条件：空运行目录和数据库初始化命令。
- 输入数据：一次包含HITL中断与恢复的Run。
- 执行步骤：初始化、运行至中断、检查两库表结构、恢复并完成Run。
- 预期结果：业务库无LangGraph内部表，checkpoint库无业务表；审计快照和恢复状态各自完整。
- 异常或边界条件：删除checkpoint副本不应破坏业务审计记录；禁止跨库事务假设。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-016 OpenAPI生成类型漂移

- 关联 Spec / FR / User Story：SPEC-004 第1、3、4、12节；AC-004-01
- 测试目标：验证Pydantic/OpenAPI是接口单一来源且生成的TypeScript类型无未提交漂移。
- 前置条件：类型生成脚本和已提交基线类型。
- 输入数据：当前OpenAPI；一次故意修改的响应字段。
- 执行步骤：生成类型并检查工作区差异；修改Schema后再次执行。
- 预期结果：当前契约无差异；Schema变化但未更新类型时CI失败，更新后恢复。
- 异常或边界条件：可选字段、枚举和Problem Details类型变化。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-017 评测数据清单完整性

- 关联 Spec / FR / User Story：SPEC-005 第2～4、15节；AC-005-01
- 测试目标：验证2个演示案件和20个离线案件具有固定目录、唯一case_id及完整金标文件。
- 前置条件：评测fixtures已创建。
- 输入数据：`fixtures/demo/`和`evals/credit-review-poc-v1/cases/`。
- 执行步骤：扫描manifest、Hash、类别数量和六类gold文件，检查材料均为纯合成数据。
- 预期结果：共22例；20例类别最低数量满足规范；无重复ID、缺失文件或Hash漂移。
- 异常或边界条件：场景标签交叉、孤立gold文件、manifest引用不存在材料。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-WF-018 工程与契约骨架冒烟

- 关联 Spec / FR / User Story：SPEC-003 第3、8、9节；SPEC-004 第1、3～8节；AC-003-01/AC-003-03/AC-004-01/AC-004-02
- 测试目标：验证工程骨架可启动，案件、材料、Run、幂等、RBAC、OpenAPI 和 Worker 报告复核关口契约可运行。
- 前置条件：Python 依赖已安装；测试使用 SQLite、MemorySaver 和 Mock 适配器，不调用真实外部 API。
- 输入数据：四类合成材料、demo-rm、demo-reviewer、重复 Idempotency-Key 和一条待处理 Run。
- 执行步骤：执行健康检查；创建案件并上传四类材料；创建 Run 并重复提交；检查 OpenAPI；领取任务并运行 Worker 一次；查询进度。
- 预期结果：API 返回 201/202；重复请求返回同一资源；Reviewer/RM 权限边界生效；任务具有租约；Worker 将 Run 推进至 `WAITING_REPORT_REVIEW`；OpenAPI 包含契约路由。
- 异常或边界条件：缺失用户、越权创建、过期版本和同 Key 不同请求均返回 Problem Details；不接入真实 DashScope/MinerU。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS
- 证据或日志引用：`backend/tests/test_contracts.py`；本地执行记录：`pytest -p no:cacheprovider`（19 passed）。

## TC-WF-019 材料事实闭环与HITL-1

- 关联 Spec / FR / User Story：SPEC-002 第6.1、6.2、9节；SPEC-003 第6、7、10节；SPEC-004 第9、10节；AC-002-01/AC-002-02/AC-003-05
- 测试目标：验证Worker完成材料解析、事实快照和实质矛盾检测后，仅在需要时暂停FACT_REVIEW，并支持Reviewer裁定、幂等重放和继续工作流。
- 前置条件：四类纯合成DOCX/XLSX材料、24/48个月期限冲突、Reviewer身份和可用SQLite任务队列。
- 输入数据：DEMO-HIGH-001的期限候选值及证据ID。
- 执行步骤：创建Run；Worker执行一次；查询事实与冲突；Reviewer选择48个月来源值；重复同一幂等请求；查询最终快照。
- 预期结果：裁定前Run=WAITING_FACT_REVIEW；所有冲突候选可回查证据；过期版本被拒绝；裁定后Run进入WAITING_REPORT_REVIEW；重复请求不重复写入。
- 异常或边界条件：RM提交返回403；错误证据返回400；同幂等键不同payload返回409；请求补件进入RETURNED并保留原因。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；`19 passed`）。
- 证据或日志引用：`backend/tests/test_contracts.py::test_material_fact_gate_human_selection_and_idempotency`。

## TC-WF-020 制度检索与规则执行工作流

- 关联 Spec / FR / User Story：SPEC-002 第6、10节；SPEC-003 第8、9节；SPEC-004 第11节；AC-002-01/AC-002-03/AC-003-05/AC-004-06
- 测试目标：验证材料事实闭环后Worker进入制度检索、只读工具和十条规则节点，并将快照引用带入报告复核前状态。
- 前置条件：正常四类材料、高风险24/48个月材料、合成制度索引、规则包和本地Mock工具。
- 输入数据：DEMO-NORMAL-001、DEMO-HIGH-001。
- 执行步骤：分别启动Run；Worker执行；查询review-results；高风险案件先完成HITL-1再查询R07和制度证据。
- 预期结果：正常案件summary=PASS且10条规则全PASS；高风险裁定48个月后summary=NON_COMPLIANT、R07=FAIL；Retrieval/Tool/Rule快照可回查，制度命中包含chunk定位和quote_hash。
- 异常或边界条件：工具失败返回NEEDS_REVIEW；缺制度证据不得伪造规则结论；RM不得读取完整Reviewer结果。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；`19 passed`）。
- 证据或日志引用：`backend/tests/test_contracts.py::test_worker_once_advances_to_report_gate`、`test_material_fact_gate_human_selection_and_idempotency`。

## TC-WF-021 HITL-2报告确认、退回与导出

- 关联 Spec / FR / User Story：SPEC-002 第11节；SPEC-003 第8、10节；SPEC-004 第10、11节；AC-002-01/AC-002-04/AC-002-07
- 测试目标：验证报告草稿生成、Reviewer确认/退回、RM可见性、幂等和Markdown导出。
- 前置条件：正常案件已完成规则、风险和报告快照；demo-rm与demo-reviewer已配置。
- 输入数据：正常报告草稿、CONFIRM_DRAFT、RETURN_FOR_RERUN及重复幂等请求。
- 执行步骤：Reviewer查看草稿；RM尝试提前查看；Reviewer确认并重复提交；查询确认报告并导出；独立Run执行退回。
- 预期结果：RM在确认前403；确认后Run=COMPLETED且RM可查看/导出；退回要求原因并将Run=RETURNED；重复请求不产生重复快照或决策。
- 异常或边界条件：过期报告版本409；REVIEW_BLOCKED或UNSUPPORTED报告禁止确认；非Reviewer执行报告操作403。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；`19 passed`）。
- 证据或日志引用：`backend/tests/test_contracts.py::test_report_review_confirm_visibility_and_markdown_export`、`test_report_review_return_for_rerun_requires_reason`。

## TC-WF-022 22例评测与工作流硬门槛

- 关联 Spec / FR / User Story：SPEC-003 第9、10节；SPEC-005 第3、9、12、15节；AC-005-01/02/05
- 测试目标：验证离线案件、演示案件、HITL声明和恢复元数据满足交付门槛。
- 前置条件：固定夹具、规则包、制度索引和本地Mock工具。
- 输入数据：20个离线案件、DEMO-NORMAL-001、DEMO-HIGH-001。
- 执行步骤：运行夹具生成器、评测器、后端测试、数据库迁移和OpenAPI检查。
- 预期结果：20例离线数据完整；两条演示路径通过；HITL-2对所有案件强制声明；规则硬门槛和安全门槛通过。
- 异常或边界条件：租约恢复、外部调用重试、工具失败、报告退回和幂等重放。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；22 passed；评测状态VERIFIED）。
- 证据或日志引用：`backend/tests/`；`scripts/run_eval.py`；`artifacts/evaluations/local-baseline/summary.json`。

## TC-WF-023 PoC最终验收门槛

- 关联 Spec / FR / User Story：SPEC-002～005；AC-005-01～06
- 测试目标：验证PoC在真实外部服务冒烟、后端/前端质量检查、数据库迁移、安全扫描和评测硬门槛全部通过后才可标记验收通过。
- 前置条件：DashScope、MinerU测试凭据已通过环境变量注入；所有输入均为合成数据。
- 输入数据：真实服务最小冒烟Query/文档、20个离线案件、2个演示案件。
- 执行步骤：执行外部冒烟；执行pytest、Ruff、Pyright、前端检查、迁移、OpenAPI、安全扫描和`run_eval.py --strict`；核对脱敏证据。
- 预期结果：外部服务响应成功；规则硬门槛、评测、权限、安全和前后端契约全部通过；不记录密钥或原始外部响应；SPEC-001 Hash不变。
- 异常或边界条件：凭据缺失、外部超时、模型别名变化、MinerU任务失败或证据中出现敏感信息。
- 自动化状态：MANUAL
- 最近执行结果：PASS（2026-08-11；真实外部冒烟、后端/前端检查、迁移、评测和安全门槛均通过）。
- 证据或日志引用：`artifacts/external-smoke/final-acceptance-dashscope.json`、`final-acceptance-mineru.json`；`artifacts/evaluations/final-acceptance/`。
