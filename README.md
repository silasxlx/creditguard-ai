# CreditGuard AI PoC

授信智能合规审查平台的PoC实现，按 `SPEC-002`～`SPEC-005` 采用Spec-first方式建设。

当前阶段提供：

- FastAPI `/api/v1` 案件、材料、Run 和进度契约；
- SQLite 业务库与任务租约表；
- LangGraph State 和可持久化 Checkpoint 适配边界；
- 独立 Worker 的 Mock 运行入口；
- PDF/DOCX/XLSX材料解析、15字段事实抽取、证据定位、冲突检测和HITL-1；
- 五份合成制度知识库、BM25 + Dense + RRF + Reranker检索链路；
- 三个只读工具和R01～R10确定性规则执行，支持规则/检索/工具快照查询；
- 固定报告模板、风险证据校验、HITL-2确认/退回和Markdown导出；
- Vue 3 + TypeScript 最小工作台壳；
- OpenAPI、单元测试、Mock E2E、合成评测集和安全门槛配置。

默认使用本地确定性Embedding/Reranker和合成工具数据；配置DashScope/MinerU密钥后才启用对应外部适配器。本PoC仍不执行最终授信审批、放款或真实客户系统写入。

## 本地启动

```powershell
uv sync
.\dev.ps1
```

也可以分别启动：

```powershell
uv run uvicorn app.main:app --app-dir backend --reload
uv run --directory backend python -m app.worker --once
npm.cmd --prefix web install
npm.cmd --prefix web run dev
```

接口文档：`http://127.0.0.1:8000/docs`

## 测试与质量检查

```powershell
uv run pytest
uv run ruff check backend
uv run pyright
uv run alembic -c backend/alembic.ini upgrade head
npm.cmd --prefix web run check
```

## 评测与安全门槛

评测只使用合成案件和合成制度，不访问真实外部 API：

```powershell
uv run python scripts/generate_eval_fixtures.py --force
uv run python scripts/run_eval.py --strict
uv run python scripts/security_scan.py --json
uv run python scripts/check_openapi_contract.py
```

评测结果写入被 Git 忽略的 `artifacts/evaluations/{timestamp}/`。其中确定性规则、
制度夹具、HITL-2声明和 `UNSUPPORTED` 结论属于硬门槛；字段抽取、RAG质量、人工量表、
时延与成本记录为首版基线，不将未校准的模型分数当作阻断阈值。

全部业务实现仍须遵循 [SPEC/SPEC-000-project-governance.md](SPEC/SPEC-000-project-governance.md)。
