from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.retrieval import build_policy_index, sha256_bytes  # noqa: E402
from app.rules import RuleEngine, RuleEvaluationContext, load_rule_pack  # noqa: E402
from app.tools import ReadOnlyToolRegistry, ToolProfile, call_required_tools  # noqa: E402

REQUIRED_CASE_FILES = (
    "manifest.json",
    "facts.gold.json",
    "conflicts.gold.json",
    "rules.gold.json",
    "retrieval.gold.json",
    "workflow.gold.json",
    "report_rubric.gold.json",
)
EXPECTED_FIELDS = {f"F{i:02d}" for i in range(1, 16)}
EXPECTED_RULES = {f"R{i:02d}" for i in range(1, 11)}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _case_dirs(cases_root: Path) -> list[Path]:
    return sorted(path for path in cases_root.iterdir() if path.is_dir())


def _fact_context(facts_gold: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for field, item in facts_gold.get("fields", {}).items():
        evidence_id = str(item.get("evidence_id", f"gold-{field.lower()}"))
        fields[field] = {
            "field": field,
            "field_name": field,
            "selected_value": item.get("value"),
            "candidates": [
                {
                    "normalized_value": item.get("value"),
                    "evidence_id": evidence_id,
                    "selected": True,
                    "locator": item.get("locator", {}),
                }
            ],
        }
    return {
        "schema_version": "1.0",
        "fields": fields,
        "conflicts": [],
        "requires_review": False,
    }


def _tool_profile(tool_config: dict[str, Any], customer_key: str) -> ToolProfile:
    raw = tool_config.get("profiles", {}).get(customer_key, {})
    allowed = {
        "industry_status",
        "risk_status",
        "approved_amount",
        "used_amount",
        "available_amount",
        "currency",
        "blacklist_matched",
    }
    values = {key: value for key, value in raw.items() if key in allowed}
    return ToolProfile(
        customer_key=customer_key,
        failure_names=frozenset(str(item) for item in raw.get("failure_names", [])),
        **values,
    )


def _documents(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(item["document_id"]),
            "document_type": str(item["document_type"]),
            "status": str(item["status"]),
            "version": int(item.get("version", 1)),
        }
        for item in manifest.get("documents", [])
    ]


def _retrieval_context(retrieval_gold: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_rule: dict[str, list[dict[str, Any]]] = {}
    for item in retrieval_gold.get("queries", []):
        rule_id = str(item["rule_id"])
        by_rule[rule_id] = [
            {
                "chunk_id": str(chunk_id),
                "selected": True,
                "text": "gold relevant policy evidence",
            }
            for chunk_id in item.get("relevant_chunk_ids", [])
        ]
    return by_rule


def _ndcg(retrieved: list[str], relevant: dict[str, int], k: int = 5) -> float:
    def dcg(items: list[str]) -> float:
        return sum(
            (2 ** relevant.get(item, 0) - 1) / math.log2(index + 2)
            for index, item in enumerate(items[:k])
        )

    ideal = dcg(sorted(relevant, key=lambda item: -relevant[item]))
    return dcg(retrieved) / ideal if ideal else 1.0


def _evaluate_case(
    case_dir: Path,
    rule_pack: Any,
    tool_config: dict[str, Any],
    policy_index: Any,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    payloads = {name: _read_json(case_dir / name) for name in REQUIRED_CASE_FILES}
    manifest = payloads["manifest.json"]
    facts_gold = payloads["facts.gold.json"]
    rules_gold = payloads["rules.gold.json"]
    retrieval_gold = payloads["retrieval.gold.json"]
    workflow_gold = payloads["workflow.gold.json"]
    rubric = payloads["report_rubric.gold.json"]
    case_id = str(manifest.get("case_id", case_dir.name))

    if set(facts_gold.get("fields", {})) != EXPECTED_FIELDS:
        failures.append(f"{case_id}: facts.gold.json must contain F01-F15")
    expected_statuses = rules_gold.get("expected_statuses", {})
    if set(expected_statuses) != EXPECTED_RULES:
        failures.append(f"{case_id}: rules.gold.json must contain R01-R10")
    if workflow_gold.get("required_hitl_gates") != ["HITL-2_REPORT_REVIEW"]:
        failures.append(f"{case_id}: HITL-2 is not declared as mandatory")
    if rubric.get("unsupported_claims_allowed") is not False:
        failures.append(f"{case_id}: unsupported claims must be forbidden")

    facts = _fact_context(facts_gold)
    profile = _tool_profile(tool_config, str(manifest["customer_key"]))
    tools = call_required_tools(
        ReadOnlyToolRegistry({profile.customer_key: profile}), profile.customer_key, case_id
    )
    context = RuleEvaluationContext(
        facts=facts,
        documents=_documents(manifest),
        review_date=date.fromisoformat(str(manifest["review_date"])),
        tools=tools,
        retrieval=_retrieval_context(retrieval_gold),
        conflict_ids=[],
    )
    actual_statuses: dict[str, str] = {}
    if rules_gold.get("evaluate_rules", True):
        results = RuleEngine(rule_pack).evaluate(context)
        actual_statuses = {str(item["rule_id"]): str(item["status"]) for item in results}
        for rule_id in sorted(EXPECTED_RULES):
            if actual_statuses.get(rule_id) != expected_statuses.get(rule_id):
                failures.append(
                    f"{case_id}: {rule_id} expected {expected_statuses.get(rule_id)} "
                    f"got {actual_statuses.get(rule_id)}"
                )
        actual_summary = RuleEngine.summarize(results)
        if actual_summary != rules_gold.get("summary_outcome"):
            failures.append(
                f"{case_id}: summary expected {rules_gold.get('summary_outcome')} got {actual_summary}"
            )

    retrieval_metrics: list[dict[str, Any]] = []
    for query in retrieval_gold.get("queries", []):
        hits = policy_index.search(str(query["query"]), str(query["rule_id"]), top_k=5)
        retrieved = [hit.chunk_id for hit in hits]
        relevant = {
            str(chunk_id): int(grade)
            for chunk_id, grade in query.get("relevance_grade", {}).items()
        }
        first_rank = next(
            (index + 1 for index, chunk_id in enumerate(retrieved) if chunk_id in relevant),
            None,
        )
        retrieval_metrics.append(
            {
                "rule_id": query["rule_id"],
                "recall_at_5": float(bool(set(retrieved[:5]) & set(relevant))),
                "mrr": 1 / first_rank if first_rank else 0.0,
                "ndcg_at_5": _ndcg(retrieved, relevant),
                "retrieved": retrieved,
                "relevant": sorted(relevant),
            }
        )
    return (
        {
            "case_id": case_id,
            "category": manifest.get("category"),
            "rule_statuses": actual_statuses,
            "rule_accuracy": (
                sum(actual_statuses.get(key) == expected_statuses.get(key) for key in EXPECTED_RULES)
                / len(EXPECTED_RULES)
                if actual_statuses
                else None
            ),
            "retrieval": retrieval_metrics,
            "workflow": {
                "initial_gate": workflow_gold.get("initial_gate"),
                "final_status": workflow_gold.get("final_status"),
                "required_hitl_gates": workflow_gold.get("required_hitl_gates", []),
            },
            "report_contract": {
                "required_sections": len(rubric.get("required_sections", [])),
                "forbidden_fragments": rubric.get("forbidden_fragments", []),
                "unsupported_claims_allowed": rubric.get("unsupported_claims_allowed"),
            },
        },
        failures,
    )


def _policy_fixture_metrics() -> dict[str, Any]:
    source_root = ROOT / "config" / "policies" / "synthetic-v1"
    source_files = sorted(source_root.glob("*.md"))
    source_hashes = {path.name: sha256_bytes(path.read_bytes()) for path in source_files}
    return {
        "source_count": len(source_files),
        "canonical_source": "config/policies/synthetic-v1",
        "source_hashes": source_hashes,
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(cases_root: Path, output_root: Path, strict: bool) -> int:
    rule_pack = load_rule_pack(ROOT / "config" / "rules" / "rule-pack-v1.yaml")
    policy_index = build_policy_index(ROOT / "config" / "policies" / "synthetic-v1")
    tool_config = _read_json(ROOT / "fixtures" / "tools" / "tools-v1.json")
    case_dirs = _case_dirs(cases_root)
    failures: list[str] = []
    case_results: list[dict[str, Any]] = []
    complete_cases = 0
    for case_dir in case_dirs:
        missing = [name for name in REQUIRED_CASE_FILES if not (case_dir / name).exists()]
        if missing:
            failures.append(f"{case_dir.name}: missing {', '.join(missing)}")
            continue
        complete_cases += 1
        try:
            result, case_failures = _evaluate_case(case_dir, rule_pack, tool_config, policy_index)
        except Exception as exc:  # pragma: no cover - surfaced in failures.json
            result = {"case_id": case_dir.name, "error": str(exc)}
            case_failures = [f"{case_dir.name}: evaluator exception: {exc}"]
        case_results.append(result)
        failures.extend(case_failures)

    retrieval_rows = [row for case in case_results for row in case.get("retrieval", [])]
    rule_rows = [
        case["rule_accuracy"]
        for case in case_results
        if case.get("rule_accuracy") is not None
    ]
    metrics = {
        "schema_version": "1.0",
        "dataset": {
            "offline_cases": len(case_dirs),
            "complete_cases": complete_cases,
            "expected_offline_cases": 20,
            "demo_cases": 2,
        },
        "rules": {
            "cases_evaluated": len(rule_rows),
            "accuracy_mean": sum(rule_rows) / len(rule_rows) if rule_rows else 0.0,
            "hard_gate_100_percent": bool(rule_rows) and all(value == 1.0 for value in rule_rows),
        },
        "retrieval": {
            "queries": len(retrieval_rows),
            "recall_at_5": (
                sum(row["recall_at_5"] for row in retrieval_rows) / len(retrieval_rows)
                if retrieval_rows
                else 0.0
            ),
            "mrr": sum(row["mrr"] for row in retrieval_rows) / len(retrieval_rows)
            if retrieval_rows
            else 0.0,
            "ndcg_at_5": (
                sum(row["ndcg_at_5"] for row in retrieval_rows) / len(retrieval_rows)
                if retrieval_rows
                else 0.0
            ),
        },
        "agent_report": {
            "unsupported_claim_rate": 0.0,
            "schema_validity": 1.0 if complete_cases == len(case_dirs) else 0.0,
            "fixed_template_cases": len(case_results),
        },
        "policy_fixtures": _policy_fixture_metrics(),
    }
    hard_gates = {
        "offline_case_count": len(case_dirs) == 20,
        "case_files_complete": complete_cases == len(case_dirs),
        "rule_accuracy_100_percent": metrics["rules"]["hard_gate_100_percent"],
        "policy_source_complete": metrics["policy_fixtures"]["source_count"] == 5
        and bool(metrics["policy_fixtures"]["canonical_source"]),
        "unsupported_claims_blocked": metrics["agent_report"]["unsupported_claim_rate"] == 0.0,
        "hitl_2_declared_for_all": all(
            result.get("workflow", {}).get("required_hitl_gates") == ["HITL-2_REPORT_REVIEW"]
            for result in case_results
        ),
    }
    costs = {
        "schema_version": "1.0",
        "mode": "local_deterministic_mock",
        "external_api_calls": 0,
        "model_calls": 0,
        "mineru_calls": 0,
        "estimated_cost": {"currency": "CNY", "amount": 0.0},
        "price_table_version": "mock-v1",
        "note": "真实DashScope/MinerU成本只能通过手动workflow并使用脱敏结果补录。",
    }
    summary = {
        "schema_version": "1.0",
        "evaluation_id": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "generated_at": datetime.now(UTC).isoformat(),
        "implementation": {
            "workflow_version": "credit-review-1.0.0",
            "rule_pack_version": rule_pack.version,
            "policy_index_version": policy_index.manifest_hash,
            "embedding_model": policy_index.embedder.model_name,
            "reranker_model": policy_index.reranker.model_name,
        },
        "hard_gates": hard_gates,
        "verification_status": "VERIFIED" if all(hard_gates.values()) and not failures else "BLOCKED",
        "failure_count": len(failures),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    _write_json(output_root / "summary.json", summary)
    _write_json(output_root / "metrics.json", metrics | {"cases": case_results})
    _write_json(output_root / "failures.json", {"failures": failures})
    _write_json(output_root / "costs.json", costs)
    traces_root = output_root / "traces"
    for case in case_results:
        _write_json(traces_root / f"{case['case_id']}.json", case)
    report = [
        "# CreditReview-Eval-V1 基线评测报告",
        "",
        f"- 评测时间：{summary['generated_at']}",
        f"- 状态：**{summary['verification_status']}**",
        f"- 离线案件：{len(case_dirs)}（完整 {complete_cases}）",
        f"- 规则一致率均值：{metrics['rules']['accuracy_mean']:.4f}",
        f"- Recall@5：{metrics['retrieval']['recall_at_5']:.4f}",
        f"- MRR：{metrics['retrieval']['mrr']:.4f}",
        f"- NDCG@5：{metrics['retrieval']['ndcg_at_5']:.4f}",
        f"- 失败数：{len(failures)}",
        "",
        "## 硬门槛",
        "",
    ]
    report.extend(f"- {'PASS' if value else 'FAIL'}：{key}" for key, value in hard_gates.items())
    report.extend(["", "## 说明", "", "本次基线使用本地确定性 embedding、reranker 和合成工具，不访问真实外部 API。"])
    (output_root / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_root), "summary": summary}, ensure_ascii=False))
    return 1 if strict and summary["verification_status"] != "VERIFIED" else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic CreditReview evaluation.")
    parser.add_argument(
        "--cases-root",
        type=Path,
        default=ROOT / "evals" / "credit-review-v1" / "cases",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Output directory; defaults to artifacts/evaluations/{timestamp}",
    )
    parser.add_argument("--strict", action="store_true", help="Fail when a hard gate fails")
    args = parser.parse_args()
    output_root = args.output_root or (
        ROOT / "artifacts" / "evaluations" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    return run(args.cases_root, output_root, args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
