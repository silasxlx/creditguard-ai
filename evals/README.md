# CreditReview-Eval-PoC-V1

离线评测集全部为合成数据。使用以下命令重新生成固定夹具：

```powershell
uv run python scripts/generate_eval_fixtures.py --force
```

运行确定性基线评测：

```powershell
uv run python scripts/run_eval.py --strict
```

评测产物写入被 Git 忽略的 `artifacts/evaluations/{timestamp}/`，包括：

```text
summary.json
metrics.json
report.md
failures.json
costs.json
traces/
```

评测集包含 20 个离线案件，另有 `fixtures/demo` 下的 2 个演示案件。固定制度源文本位于
`config/policies/synthetic-v1`，工具夹具位于 `fixtures/tools/tools-v1.json`。
