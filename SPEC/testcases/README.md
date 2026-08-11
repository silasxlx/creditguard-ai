# 测试样例治理与目录

本目录用于持续积累授信智能审查项目的测试样例、执行状态和证据引用。行为要求由 [SPEC-000](../SPEC-000-project-governance.md) 统一规定。

## 领域目录

| 领域 | 文件 | 编号前缀 | SPEC-001 基线 | 当前已登记 |
|---|---|---|---|---|
| 文档解析 | [document.md](./document.md) | `TC-DOC-` | 001～003 | 004～014 |
| RAG | [rag.md](./rag.md) | `TC-RAG-` | 001～004 | 005～013 |
| 规则引擎 | [rule.md](./rule.md) | `TC-RULE-` | 001～004 | 005～012 |
| Agent | [agent.md](./agent.md) | `TC-AGENT-` | 001～003 | 004～015 |
| Workflow | [workflow.md](./workflow.md) | `TC-WF-` | 001～002 | 003～030 |
| Security | [security.md](./security.md) | `TC-SEC-` | 001～003 | 004～022 |

已有基线测试的正文仍以 [SPEC-001 第 43～49 节](../SPEC-001-credit-review-platform-v1.md#43-test-strategy) 为准，本目录只登记引用，不复制第二份正文。

PoC 新增样例依据 [SPEC-002](../SPEC-002-credit-review-poc-scope-v1.md)、[SPEC-003](../SPEC-003-credit-review-architecture-poc-v1.md)、[SPEC-004](../SPEC-004-credit-review-contracts-poc-v1.md)、[SPEC-005](../SPEC-005-credit-review-evaluation-poc-v1.md) 和 [SPEC-006](../SPEC-006-github-release-and-demo-v1.md) 登记。尚未实现的领域保持 `PLANNED / NOT_RUN`；已完成实现的样例必须登记自动化状态、执行结果和代码证据，例如 `TC-WF-018`。

## 测试样例模板

新增样例写入对应领域文件，并使用以下结构：

```markdown
## TC-{DOMAIN}-{NNN} 测试名称

- 关联 Spec / FR / User Story：
- 测试目标：
- 前置条件：
- 输入数据：
- 执行步骤：
  1. 
- 预期结果：
- 异常或边界条件：
- 自动化状态：PLANNED | MANUAL | AUTOMATED | NOT_APPLICABLE
- 最近执行结果：NOT_RUN | PASS | FAIL | BLOCKED
- 证据或日志引用：
```

## 编号规则

- 在对应领域当前最大编号后递增。
- 编号一经登记不得复用。
- 废弃样例保留原编号并标记 `DEPRECATED`。
- 表格中的引用不是新的测试定义；正式定义以 `## TC-...` 标题为准。
- 提交前检查所有正式定义标题不存在重复编号。

## 执行记录

每次执行至少更新：

- 执行日期；
- 被测 Spec、规则、Prompt、模型或代码版本；
- 执行环境；
- PASS / FAIL / BLOCKED；
- 失败原因；
- 日志、截图、Trace 或报告引用。

测试结果不得包含密码、Token 或未脱敏客户数据。
