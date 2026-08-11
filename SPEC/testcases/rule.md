# Rule Engine 测试样例

## SPEC-001 基线引用

| Test Case ID | 名称 | 来源 |
|---|---|---|
| `TC-RULE-001` | 正常期限 | SPEC-001 第 44 节 |
| `TC-RULE-002` | 超期限 | SPEC-001 第 44 节 |
| `TC-RULE-003` | 边界值 | SPEC-001 第 44 节 |
| `TC-RULE-004` | 空值 | SPEC-001 第 44 节 |

新增操作符、组合条件、版本、生效日期、输入快照和证据绑定测试从 `TC-RULE-005` 开始，格式遵循 [测试样例模板](./README.md#测试样例模板)。

## 新增测试样例

## TC-RULE-005 安全规则包与Hash

- 关联 Spec / FR / User Story：SPEC-003 第9节；SPEC-004 第11节
- 测试目标：验证YAML只允许白名单操作符且同版本Hash不可漂移。
- 前置条件：规则加载器可用。
- 输入数据：有效规则包、含eval/动态表达式规则包、同版本不同内容规则包。
- 执行步骤：依次加载并执行校验。
- 预期结果：仅有效规则包加载；其余明确失败且不执行任意代码。
- 异常或边界条件：未知操作符和未知财务函数。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RULE-006 十条规则金标一致性

- 关联 Spec / FR / User Story：SPEC-002 第10节；SPEC-005 第7节
- 测试目标：验证R01～R10在正常、违反和缺失输入下与金标一致。
- 前置条件：版本1.0.0规则包和工具Mock。
- 输入数据：每条规则至少PASS、FAIL或NEEDS_REVIEW参数组。
- 执行步骤：表驱动执行全部参数组。
- 预期结果：结果、消息、证据和规则版本100%匹配金标。
- 异常或边界条件：类型错误和空字符串。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RULE-007 规则边界值

- 关联 Spec / FR / User Story：SPEC-002 第10节
- 测试目标：验证1年、36月、70%、1.0及额度等于申请额的包含边界。
- 前置条件：计算基准日固定。
- 输入数据：成立日周年边界（含2月29日）、36月、70%、1.0及额度等于/刚低于/刚高于阈值，另含负数、币种不一致和未来成立日。
- 执行步骤：使用Decimal和程序日期计算执行规则。
- 预期结果：使用固定review_date；非闰年2月29日周年按2月28日；等于允许边界时PASS，越界时FAIL；负数、未来日期、币种不一致和零分母为NEEDS_REVIEW。
- 异常或边界条件：无效日期、期限为0、可用额度为0、极高精度Decimal。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RULE-008 WARN语义

- 关联 Spec / FR / User Story：SPEC-002 第10节
- 测试目标：验证受限行业或客户关注状态返回WARN。
- 前置条件：行业制度和客户工具Mock。
- 输入数据：ALLOWED/RESTRICTED/PROHIBITED及NORMAL/WATCH/HIGH_RISK。
- 执行步骤：执行R03和R05。
- 预期结果：RESTRICTED/WATCH为WARN，PROHIBITED/HIGH_RISK为FAIL，其余PASS。
- 异常或边界条件：未知枚举返回NEEDS_REVIEW。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RULE-009 缺失、冲突和工具失败

- 关联 Spec / FR / User Story：SPEC-002 第9、10节；AC-002-06
- 测试目标：验证不确定输入不会被误判PASS或FAIL。
- 前置条件：规则输入解析完成。
- 输入数据：字段缺失、冲突未裁定、工具超时和无效返回。
- 执行步骤：执行依赖对应输入的规则。
- 预期结果：均返回NEEDS_REVIEW并阻断报告确认，保留原因。
- 异常或边界条件：非关键工具结果缺失。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RULE-010 财务Decimal计算

- 关联 Spec / FR / User Story：SPEC-003 第9节
- 测试目标：验证资产负债率和流动比率使用Decimal及预注册公式。
- 前置条件：F10～F13已规范化。
- 输入数据：正常值、重复小数、分母为零和缺字段。
- 执行步骤：用Decimal计算 `total_liabilities / total_assets * 100%` 和 `current_assets / current_liabilities` 并执行R09/R10。
- 预期结果：资产负债率<=70%和流动比率>=1.0时PASS，越界FAIL；零/负分母、任一负值和缺字段NEEDS_REVIEW；无任意代码执行。
- 异常或边界条件：极大金额、重复小数和精度量化策略不改变边界结果。
- 自动化状态：PLANNED
- 最近执行结果：NOT_RUN
- 证据或日志引用：待实现后补充。

## TC-RULE-011 十条规则执行与工具失败隔离

- 关联 Spec / FR / User Story：SPEC-002 第10节；SPEC-003 第7节；SPEC-004 第11节；AC-002-03/AC-002-06/AC-003-06
- 测试目标：验证R01～R10可由不可变YAML规则包执行，边界结果和工具失败语义符合规范。
- 前置条件：rule-pack-v1.yaml、完整事实快照、三个只读工具Mock和制度检索证据。
- 输入数据：正常案件、期限37个月、工具check_blacklist失败及未知规则predicate。
- 执行步骤：加载规则包；执行十条规则；检查36个月、70%、1.0边界；注入工具失败；尝试加载未知predicate。
- 预期结果：正常十条均PASS；期限37个月R07=FAIL；工具失败对应规则=NEEDS_REVIEW；未知predicate拒绝加载；规则结果带证据引用和规则Hash。
- 异常或边界条件：负数、币种不一致、零分母和缺失事实不能得到PASS/FAIL确定结论。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；`15 passed`）。
- 证据或日志引用：`backend/tests/test_retrieval_rules.py::test_rule_pack_has_ten_rules_and_enforces_boundaries`、`test_tool_failure_is_needs_review_and_unknown_rule_is_rejected`。

## TC-RULE-012 R01～R10确定性规则硬门槛

- 关联 Spec / FR / User Story：SPEC-002 第10节；SPEC-004 第11节；SPEC-005 第7、15节；AC-005-02
- 测试目标：验证20个离线金标案件中R01～R10结果与边界依据100%一致。
- 前置条件：规则包版本和Hash已固定，确定性工具夹具可用。
- 输入数据：正常、边界、冲突、缺件和工具失败案件。
- 执行步骤：运行规则评测；比较每个rule_id状态、摘要和边界指标。
- 预期结果：规则一致率100%；缺数据、工具失败和未裁定冲突不会被判为PASS；失败时PoC不能标记VERIFIED。
- 异常或边界条件：等于36个月、70%、1.0和额度相等边界；类型错误、空值和币种不一致。
- 自动化状态：AUTOMATED
- 最近执行结果：PASS（2026-08-10；规则一致率1.0）。
- 证据或日志引用：`scripts/run_eval.py`；`artifacts/evaluations/local-baseline/summary.json`。
