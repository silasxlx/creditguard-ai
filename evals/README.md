# CreditReview-Eval-V1

离线评测集全部使用合成数据，覆盖正常、规则边界、材料冲突、缺件、工具失败和恢复场景。

重新生成固定夹具：

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

固定制度源文本位于 `config/policies/synthetic-v1`，工具夹具位于 `fixtures/tools/tools-v1.json`。公开仓库不包含真实客户材料、真实制度或外部服务原始响应。
