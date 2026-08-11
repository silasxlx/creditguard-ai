# CreditGuard AI 项目行为与治理规范

**编号：SPEC-000**  
**版本：V1.0**  
**状态：ACTIVE**  
**适用范围：授信智能合规审查平台的需求、设计、开发、修复、重构和文档工作**

---

## 1. 目标

本规范确立两项不可绕过的项目行为：

1. **Spec-first**：先讨论并确认 Spec，再进行正式实现。
2. **Test Case Accumulation**：所有工作产出必须新增或更新测试样例，并持续沉淀测试结果和证据。

本规范优先于个人习惯和临时口头约定。若当前任务与已确认 Spec 冲突，应暂停实现并先更新 Spec。

## 2. 强制工作流程

所有工作按以下顺序进行：

```text
需求或问题提出
  ↓
业务与技术讨论
  ↓
创建或修改 Spec
  ↓
明确范围、接口、Acceptance Criteria 和 Test Case
  ↓
Spec Review
  ↓
Spec APPROVED
  ↓
实现
  ↓
执行测试
  ↓
记录结果和证据
  ↓
更新 Spec / 测试目录 / 交付说明
```

禁止：

- Spec 未确认就开始正式编码。
- 先修改实现，交付时再反向补 Spec。
- 功能、缺陷、规则或架构发生变化但不更新测试样例。
- 测试失败、未执行或缺少证据时标记为完成。
- 用 LLM 生成的结论替代确定性测试和人工验收。

## 3. Spec 最低要求

进入 `APPROVED` 前，Spec 至少包含：

- 背景和目标；
- 范围与明确不做的内容；
- 角色、业务流程或调用方；
- 输入、输出和关键数据结构；
- 业务规则与权限边界；
- 正常、异常和边界行为；
- Acceptance Criteria；
- 对应 Test Case ID；
- 失败处理、审计和人工介入策略；
- 兼容、迁移或回滚要求（适用时）。

如果上述内容不足以让另一位工程师在不做关键决策的情况下实施，Spec 仍应保持 `DRAFT` 或 `REVIEWING`。

## 4. 变更分类和处理

以下工作都必须遵循本规范：

| 工作类型 | Spec 要求 | 测试要求 |
|---|---|---|
| 新功能 | 新增或修改 Spec | 正常、异常、边界和安全样例 |
| 缺陷修复 | 在 Spec 中确认正确行为 | 先增加可复现失败的回归样例 |
| 架构变更 | 新增架构 Spec 或 ADR | 集成、兼容、恢复和性能样例 |
| 规则变更 | 新建规则版本，禁止覆盖历史版本 | 正常值、边界值、超限值、空值和版本样例 |
| Prompt/模型变更 | 更新版本、输入输出和失败策略 | 固定评测集和回归对比 |
| 文档变更 | 更新索引和相关引用 | 链接、结构、完整性或人工检查样例 |

任何影响范围、接口、数据、规则、权限或验收标准的变更，都必须先把对应 Spec 状态退回 `DRAFT` 或 `REVIEWING`。

## 5. Spike 约定

探索性验证允许在 Spec 批准前执行，但必须满足：

- 明确标记为 `SPIKE`；
- 仅用于验证未知风险或技术可行性；
- 预先定义问题、时间盒和输出；
- 不连接真实敏感数据或生产系统；
- 不作为正式实现合并或交付；
- Spike 结论必须回写 Spec，正式实现仍需完成评审。

Spike 不能用于规避 Spec-first。

## 6. 测试样例积累

每项工作至少关联一个 Test Case ID。根据风险补充以下类型：

- Happy Path；
- 异常路径；
- 边界值和空值；
- 权限与安全；
- 数据质量和材料冲突；
- Human-in-the-loop；
- 失败恢复和幂等性；
- 回归兼容。

测试编号沿用：

```text
TC-DOC-NNN
TC-RAG-NNN
TC-RULE-NNN
TC-AGENT-NNN
TC-WF-NNN
TC-SEC-NNN
```

编号一经使用不得复用；废弃样例保留编号并标记 `DEPRECATED`。

## 7. 追溯关系

所有交付必须形成：

```text
需求或变更
→ Spec / FR / ADR
→ Acceptance Criteria
→ Test Case ID
→ 自动化测试或人工验证
→ 测试结果
→ 证据或日志引用
```

交付说明中应列出：

- 修改了哪些 Spec；
- 实现了哪些 Acceptance Criteria；
- 新增或更新了哪些 Test Case；
- 执行了哪些测试；
- 结果、未解决问题和剩余风险。

## 8. 测试结果状态

自动化状态：

```text
PLANNED
MANUAL
AUTOMATED
NOT_APPLICABLE
```

执行结果：

```text
NOT_RUN
PASS
FAIL
BLOCKED
```

不得把 `NOT_RUN` 或 `BLOCKED` 描述为通过。

## 9. Definition of Ready

正式开发开始前必须满足：

```text
□ Spec 已进入 APPROVED
□ 范围和非范围明确
□ Acceptance Criteria 明确
□ 接口和数据约束明确
□ Test Case ID 已登记
□ 安全、审计和失败处理已考虑
□ 外部依赖和阻塞项已确认
```

## 10. Definition of Done

任何工作只有满足以下条件才算完成：

```text
□ Spec 已确认
□ Acceptance Criteria 明确且已满足
□ 测试样例已新增或更新
□ 正常、异常和边界路径已覆盖
□ 测试已执行
□ 结果和证据已记录
□ 未解决问题和剩余风险已披露
□ 相关 Spec、ADR、索引和测试目录已同步更新
```

AI 功能额外要求：

```text
□ 模型和 Prompt 有版本
□ Input / Output Schema 已校验
□ Evidence 可追溯
□ Unsupported Claim 已评测
□ Tool 权限和失败策略已测试
□ Human Escalation 策略已测试
```

## 11. 规范入口

- 规范索引：[README.md](./README.md)
- 产品总规范：[SPEC-001-credit-review-platform-v1.md](./SPEC-001-credit-review-platform-v1.md)
- 测试样例治理：[testcases/README.md](./testcases/README.md)

后续新增 Spec、ADR 和测试文件时，必须同步更新规范索引。
