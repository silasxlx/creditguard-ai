# CreditGuard AI 规范目录

本目录是“授信智能合规审查平台”的规范、架构决策、测试样例和交付证据入口。项目统一采用 **Spec-first Development + Test Case Accumulation**。

## 必读顺序

1. [SPEC-000 项目行为与治理规范](./SPEC-000-project-governance.md)
2. [SPEC-001 授信智能合规审查平台 V1.0](./SPEC-001-credit-review-platform-v1.md)
3. [SPEC-002 PoC 范围规范](./SPEC-002-credit-review-poc-scope-v1.md)
4. [SPEC-003 PoC 技术架构](./SPEC-003-credit-review-architecture-poc-v1.md)
5. [SPEC-004 PoC 接口与数据契约](./SPEC-004-credit-review-contracts-poc-v1.md)
6. [SPEC-005 PoC 评测规范](./SPEC-005-credit-review-evaluation-poc-v1.md)
7. 与当前任务相关的 ADR 和 [测试样例目录](./testcases/README.md)

未完成 Spec 讨论、验收标准定义和评审确认，不得进入正式开发。

## 规范索引

| 编号 | 文档 | 状态 | 用途 |
|---|---|---|---|
| SPEC-000 | [项目行为与治理规范](./SPEC-000-project-governance.md) | ACTIVE | 规定 Spec-first、测试积累、变更和交付规则 |
| SPEC-001 | [授信智能合规审查平台 V1.0](./SPEC-001-credit-review-platform-v1.md) | DRAFT | 产品范围、用户故事、Agent、RAG、规则、MCP 和测试基线 |
| SPEC-002 | [授信审查 PoC 范围 V1.0](./SPEC-002-credit-review-poc-scope-v1.md) | APPROVED | 第一阶段业务范围、角色、演示路径、规则和验收边界 |
| SPEC-003 | [授信审查 PoC 技术架构 V1.0](./SPEC-003-credit-review-architecture-poc-v1.md) | APPROVED | 单机架构、解析、RAG、LangGraph、Worker、安全和运行方式 |
| SPEC-004 | [授信审查 PoC 接口与数据契约 V1.0](./SPEC-004-credit-review-contracts-poc-v1.md) | APPROVED | REST API、状态、State、数据表、规则、工具和HITL契约 |
| SPEC-005 | [授信审查 PoC 评测规范 V1.0](./SPEC-005-credit-review-evaluation-poc-v1.md) | APPROVED | 合成评测集、质量指标、硬门槛、CI和测试追溯 |

SPEC-001 是长期产品目标；SPEC-002～005 是第一阶段 PoC 覆盖规范。PoC 明确收窄基础设施和评测规模，但不修改或删除 SPEC-001 正文。只有 SPEC-002～005 经用户评审并进入 `APPROVED` 后，才可开始正式编码。

## Spec 状态

```text
DRAFT
  ↓
REVIEWING
  ↓
APPROVED
  ↓
IMPLEMENTING
  ↓
VERIFIED
  ↓
DONE
```

- `DRAFT`：讨论和编辑中，不允许正式开发。
- `REVIEWING`：范围、接口、验收标准和测试样例正在评审。
- `APPROVED`：评审通过，可以进入开发。
- `IMPLEMENTING`：正在按已确认 Spec 实施。
- `VERIFIED`：实现完成，测试和验收证据已记录。
- `DONE`：交付完成，相关文档已同步。

需求发生实质变化时，状态必须退回 `DRAFT` 或 `REVIEWING`，先更新 Spec，再更新实现。

## 测试样例目录

| 领域 | 文件 | 编号前缀 |
|---|---|---|
| 文档解析 | [document.md](./testcases/document.md) | `TC-DOC-` |
| RAG | [rag.md](./testcases/rag.md) | `TC-RAG-` |
| 规则引擎 | [rule.md](./testcases/rule.md) | `TC-RULE-` |
| Agent | [agent.md](./testcases/agent.md) | `TC-AGENT-` |
| Workflow | [workflow.md](./testcases/workflow.md) | `TC-WF-` |
| Security | [security.md](./testcases/security.md) | `TC-SEC-` |

新增测试样例、执行状态和证据的维护方式见 [测试样例治理说明](./testcases/README.md)。

## 文档归属规则

- 行为和交付规则写入 `SPEC-000`。
- 产品行为、接口、数据和验收标准写入对应产品 Spec。
- 跨模块架构决策写入 ADR 或架构 Spec。
- 测试样例写入 `testcases/` 对应领域文件。
- 原始材料、代码、构建产物和运行日志不存放在 `SPEC/`。
