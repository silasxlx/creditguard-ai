# CreditGuard AI 演示指南

演示使用纯合成材料和固定演示身份，不连接真实银行系统，也不产生最终授信审批结果。

## 启动

```powershell
uv sync
npm.cmd --prefix web ci
.\dev.ps1
```

打开 <http://127.0.0.1:5173>，通过顶部角色切换器在 RM 和 Reviewer 之间切换。

## 正常案件

1. 以 RM 身份创建正常演示案件。
2. 等待材料解析和规则检查完成。
3. 切换为 Reviewer，打开报告复核页面。
4. 确认报告，检查状态变为 `CONFIRMED`，并导出 Markdown。

预期结果：事实可直接使用，规则结果为 `PASS`，报告进入人工确认阶段。

## 高风险案件

1. 以 RM 身份创建高风险演示案件。
2. 切换为 Reviewer，打开事实复核页面。
3. 在申请期限冲突中选择尽调报告的 48 个月值，并填写裁定原因。
4. 打开规则与风险页面，检查 R07 为 `FAIL`，总体结果为 `NON_COMPLIANT`。
5. 在报告复核页面确认草稿，验证报告仍明确标注为 AI 辅助审查。

## 手工上传

1. 以 RM 身份创建新案件。
2. 为四类必需材料分别上传 PDF、DOCX 或 XLSX 文件。
3. 启动审查 Run，查看材料版本、解析状态和人工关口。
4. 如存在矛盾或缺件，切换 Reviewer 完成事实裁定或要求补件。

## Demo API

只有在 `CREDIT_REVIEW_DEMO_MODE=true` 时才注册固定场景接口。接口只接受两个场景 ID、RM 身份和幂等键，不接收路径、URL、SQL 或任意参数；创建过程复用正式案件、材料和 Run 服务。

## 常见问题

- Worker 找不到制度文件时，请从项目根目录启动，并确认 `PYTHONPATH` 指向 `backend`。
- Run 进入 `PAUSED_RETRYABLE` 时，Reviewer 可在确认错误类别后执行重试。
- 直接启动 API 默认关闭 Demo 路由；本地一键启动脚本会显式开启演示模式。
