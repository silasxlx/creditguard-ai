from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.retrieval import build_policy_index  # noqa: E402
from app.rules import load_rule_pack  # noqa: E402

CASE_FILES = (
    "manifest.json",
    "facts.gold.json",
    "conflicts.gold.json",
    "rules.gold.json",
    "retrieval.gold.json",
    "workflow.gold.json",
    "report_rubric.gold.json",
)
DOCUMENT_TYPES = (
    "BUSINESS_LICENSE",
    "CREDIT_APPLICATION",
    "DUE_DILIGENCE",
    "FINANCIAL_STATEMENTS",
)


@dataclass
class CaseSpec:
    case_id: str
    category: str
    tags: list[str] = field(default_factory=list)
    term: int = 24
    amount: str = "1000000"
    assets: str = "5000000"
    liabilities: str = "2000000"
    current_assets: str = "3000000"
    current_liabilities: str = "1500000"
    industry: str = "制造业"
    purpose: str = "流动资金"
    available: str = "1500000"
    risk_status: str = "NORMAL"
    blacklist: bool = False
    tool_failures: list[str] = field(default_factory=list)
    missing_documents: list[str] = field(default_factory=list)
    rejected_documents: list[str] = field(default_factory=list)
    not_ready_documents: list[str] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    expected_overrides: dict[str, str] = field(default_factory=dict)
    initial_gate: str | None = None
    final_status: str = "COMPLETED"
    recovery: dict[str, Any] = field(default_factory=dict)
    evaluate_rules: bool = True


def _case_specs() -> list[CaseSpec]:
    specs = [
        CaseSpec(f"NORMAL-{i:03d}", "normal", ["normal", "baseline"]) for i in range(1, 5)
    ]
    specs += [
        CaseSpec("BOUNDARY-001", "boundary", ["tenor_equal_36"], term=36),
        CaseSpec("BOUNDARY-002", "boundary", ["leverage_equal_70"], liabilities="3500000"),
        CaseSpec(
            "BOUNDARY-003",
            "boundary",
            ["current_ratio_equal_1"],
            current_assets="1500000",
        ),
        CaseSpec("BOUNDARY-004", "boundary", ["exposure_equal_request"], amount="1500000"),
        CaseSpec(
            "CONFLICT-001",
            "conflict",
            ["material_tenor_conflict", "hitl_1"],
            term=48,
            conflicts=[
                {
                    "field": "F08",
                    "material": True,
                    "candidate_values": [24, 48],
                    "selected_value": 48,
                    "action": "SELECT_SOURCE",
                }
            ],
            expected_overrides={"R07": "FAIL"},
        ),
        CaseSpec(
            "CONFLICT-002",
            "conflict",
            ["material_amount_conflict", "hitl_1"],
            conflicts=[
                {
                    "field": "F06",
                    "material": True,
                    "candidate_values": ["1000000", "1020000"],
                    "selected_value": "1020000",
                    "action": "SELECT_SOURCE",
                }
            ],
        ),
        CaseSpec(
            "CONFLICT-003",
            "conflict",
            ["discrete_identifier_conflict", "hitl_1"],
            conflicts=[
                {
                    "field": "F02",
                    "material": True,
                    "candidate_values": ["91310000SYNTH001", "91310000SYNTH999"],
                    "selected_value": "91310000SYNTH001",
                    "action": "SELECT_SOURCE",
                }
            ],
        ),
        CaseSpec(
            "CONFLICT-004",
            "conflict",
            ["financial_value_conflict", "hitl_1"],
            assets="5200000",
            liabilities="2000000",
            conflicts=[
                {
                    "field": "F10",
                    "material": True,
                    "candidate_values": ["5000000", "5200000"],
                    "selected_value": "5200000",
                    "action": "ENTER_REVISED_VALUE",
                }
            ],
        ),
        CaseSpec(
            "DOCUMENT-001",
            "document",
            ["missing_material", "hitl_1"],
            missing_documents=["FINANCIAL_STATEMENTS"],
            initial_gate="WAITING_FACT_REVIEW",
            evaluate_rules=True,
            expected_overrides={"R01": "FAIL"},
        ),
        CaseSpec(
            "DOCUMENT-002",
            "document",
            ["encrypted_pdf", "reupload_required"],
            rejected_documents=["BUSINESS_LICENSE"],
            initial_gate="WAITING_FACT_REVIEW",
            expected_overrides={"R01": "FAIL"},
        ),
        CaseSpec(
            "DOCUMENT-003",
            "document",
            ["xlsx_formula_cache_missing", "hitl_1"],
            not_ready_documents=["FINANCIAL_STATEMENTS"],
            initial_gate="WAITING_FACT_REVIEW",
            expected_overrides={"R01": "NEEDS_REVIEW"},
        ),
        CaseSpec(
            "RECOVERY-001",
            "recovery",
            ["lease_expiry", "resume"],
            recovery={"failure": "WORKER_LEASE_EXPIRED", "attempts": 2},
        ),
        CaseSpec(
            "RECOVERY-002",
            "recovery",
            ["external_api_retry", "resume"],
            recovery={"failure": "DASHSCOPE_TIMEOUT", "attempts": 3},
        ),
        CaseSpec(
            "RECOVERY-003",
            "recovery",
            ["tool_failure", "needs_review"],
            tool_failures=["check_blacklist"],
            expected_overrides={"R04": "NEEDS_REVIEW"},
        ),
        CaseSpec(
            "RAG-001",
            "rag",
            ["query_template", "cross_policy"],
            purpose="采购原材料",
        ),
        CaseSpec(
            "RAG-002",
            "rag",
            ["synonym_query", "restricted_industry"],
            industry="医药",
            expected_overrides={"R03": "WARN"},
        ),
    ]
    return specs


def _documents(spec: CaseSpec) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for document_type in DOCUMENT_TYPES:
        if document_type in spec.missing_documents:
            continue
        status = "PARSED"
        if document_type in spec.rejected_documents:
            status = "REJECTED"
        elif document_type in spec.not_ready_documents:
            status = "NEEDS_REVIEW"
        documents.append(
            {
                "document_id": f"{spec.case_id.lower()}-{document_type.lower()}",
                "document_type": document_type,
                "version": 1,
                "status": status,
                "filename": f"{document_type.lower()}-v1.docx",
            }
        )
    return documents


def _facts(spec: CaseSpec) -> dict[str, Any]:
    values: dict[str, Any] = {
        "F01": "合成科技有限公司",
        "F02": "91310000SYNTH001",
        "F03": "2020-01-01",
        "F04": "张三",
        "F05": spec.industry,
        "F06": spec.amount,
        "F07": "CNY",
        "F08": spec.term,
        "F09": spec.purpose,
        "F10": spec.assets,
        "F11": spec.liabilities,
        "F12": spec.current_assets,
        "F13": spec.current_liabilities,
        "F14": "8000000",
        "F15": "600000",
    }
    fields: dict[str, Any] = {}
    for field_name, value in values.items():
        fields[field_name] = {
            "field": field_name,
            "value": value,
            "evidence_id": f"{spec.case_id.lower()}-evidence-{field_name.lower()}",
            "locator": {"source": "credit-application-v1.docx", "paragraph_index": 1},
        }
    return {
        "schema_version": "1.0",
        "fields": fields,
        "requires_review": bool(spec.conflicts or spec.initial_gate),
        "selected_conflict_fields": [str(item["field"]) for item in spec.conflicts],
    }


def _expected_statuses(spec: CaseSpec) -> dict[str, str]:
    statuses = {f"R{i:02d}": "PASS" for i in range(1, 11)}
    if spec.missing_documents or spec.rejected_documents:
        statuses["R01"] = "FAIL"
    elif spec.not_ready_documents:
        statuses["R01"] = "NEEDS_REVIEW"
    if spec.industry == "医药" or spec.industry == "建筑业":
        statuses["R03"] = "WARN"
    if spec.industry in {"房地产开发", "博彩", "钢铁产能过剩行业"}:
        statuses["R03"] = "FAIL"
    if spec.blacklist:
        statuses["R04"] = "FAIL"
    if spec.risk_status == "WATCH":
        statuses["R05"] = "WARN"
    if spec.risk_status == "HIGH_RISK":
        statuses["R05"] = "FAIL"
    if spec.term > 36:
        statuses["R07"] = "FAIL"
    if float(spec.amount) > float(spec.available):
        statuses["R08"] = "FAIL"
    if float(spec.liabilities) / float(spec.assets) * 100 > 70:
        statuses["R09"] = "FAIL"
    if float(spec.current_assets) / float(spec.current_liabilities) < 1:
        statuses["R10"] = "FAIL"
    if spec.tool_failures:
        for failure in spec.tool_failures:
            if failure == "check_blacklist":
                statuses["R04"] = "NEEDS_REVIEW"
            if failure == "get_customer_profile":
                statuses["R05"] = "NEEDS_REVIEW"
            if failure == "get_credit_exposure":
                statuses["R08"] = "NEEDS_REVIEW"
    statuses.update(spec.expected_overrides)
    return statuses


def _summary(statuses: dict[str, str]) -> str:
    if "NEEDS_REVIEW" in statuses.values():
        return "REVIEW_BLOCKED"
    if "FAIL" in statuses.values():
        return "NON_COMPLIANT"
    if "WARN" in statuses.values():
        return "WARNING"
    return "PASS"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _retrieval_gold(index: Any, rule_pack: Any) -> list[dict[str, Any]]:
    queries = []
    for definition in rule_pack.rules:
        hits = index.search(definition.query_template, definition.rule_id, top_k=5)
        queries.append(
            {
                "rule_id": definition.rule_id,
                "query": definition.query_template,
                "relevant_chunk_ids": [hit.chunk_id for hit in hits[:1]],
                "relevance_grade": {hit.chunk_id: 3 for hit in hits[:1]},
            }
        )
    return queries


def _write_case(root: Path, spec: CaseSpec, retrieval_gold: list[dict[str, Any]]) -> None:
    case_root = root / spec.case_id
    case_root.mkdir(parents=True, exist_ok=True)
    documents = _documents(spec)
    statuses = _expected_statuses(spec)
    manifest = {
        "schema_version": "1.0",
        "case_id": spec.case_id,
        "category": spec.category,
        "scenario_tags": spec.tags,
        "input_version": "v1",
        "customer_key": f"SYNTH-{spec.case_id}",
        "review_date": "2026-08-10",
        "documents": documents,
        "synthetic_only": True,
        "recovery": spec.recovery,
    }
    conflicts = {
        "schema_version": "1.0",
        "conflicts": spec.conflicts,
        "expected_gate": spec.initial_gate,
        "human_action_required": bool(spec.conflicts or spec.initial_gate),
    }
    rules = {
        "schema_version": "1.0",
        "evaluate_rules": spec.evaluate_rules,
        "expected_statuses": statuses,
        "summary_outcome": _summary(statuses),
        "boundary_basis": {
            "tenor_months": spec.term,
            "leverage_percent": str(float(spec.liabilities) / float(spec.assets) * 100),
            "current_ratio": str(float(spec.current_assets) / float(spec.current_liabilities)),
            "requested_amount": spec.amount,
            "available_amount": spec.available,
        },
    }
    workflow = {
        "schema_version": "1.0",
        "expected_nodes": [
            "load_run",
            "parse_materials",
            "extract_facts",
            "normalize_validate",
            "detect_conflicts",
            "retrieve_policies",
            "tools_metrics_rules",
            "synthesize_validate_risks",
            "render_report",
        ],
        "initial_gate": spec.initial_gate,
        "required_hitl_gates": ["HITL-2_REPORT_REVIEW"],
        "final_status": spec.final_status,
        "recovery": spec.recovery,
    }
    rubric = {
        "schema_version": "1.0",
        "required_sections": [
            "# 授信智能合规审查报告",
            "## 1. 审查结论",
            "## 2. 关键事实",
            "## 3. 规则结果",
            "## 4. 风险与待办",
            "## 5. 制度依据",
            "## 6. 工具状态",
            "## 7. 限制与人工记录",
        ],
        "forbidden_fragments": ["自动批准授信", "授信审批已通过"],
        "unsupported_claims_allowed": False,
        "expected_summary_outcome": _summary(statuses),
    }
    _write_json(case_root / "manifest.json", manifest)
    _write_json(case_root / "facts.gold.json", _facts(spec))
    _write_json(case_root / "conflicts.gold.json", conflicts)
    _write_json(case_root / "rules.gold.json", rules)
    _write_json(case_root / "retrieval.gold.json", {"queries": retrieval_gold})
    _write_json(case_root / "workflow.gold.json", workflow)
    _write_json(case_root / "report_rubric.gold.json", rubric)


def generate(root: Path, force: bool = False) -> int:
    root.mkdir(parents=True, exist_ok=True)
    policy_root = ROOT / "config" / "policies" / "synthetic-v1"
    index = build_policy_index(policy_root)
    rule_pack = load_rule_pack(ROOT / "config" / "rules" / "rule-pack-v1.yaml")
    retrieval_gold = _retrieval_gold(index, rule_pack)
    specs = _case_specs()
    demo_specs = [
        CaseSpec("DEMO-NORMAL-001", "demo", ["demo", "normal"]),
        CaseSpec(
            "DEMO-HIGH-001",
            "demo",
            ["demo", "high_risk", "material_tenor_conflict"],
            term=48,
            conflicts=[
                {
                    "field": "F08",
                    "material": True,
                    "candidate_values": [24, 48],
                    "selected_value": 48,
                    "action": "SELECT_SOURCE",
                }
            ],
            expected_overrides={"R07": "FAIL"},
        ),
    ]
    for spec in specs:
        _write_case(root, spec, retrieval_gold)
    demo_root = ROOT / "fixtures" / "demo"
    for spec in demo_specs:
        _write_case(demo_root, spec, retrieval_gold)
    tools = {
        "schema_version": "1.0",
        "synthetic_only": True,
        "profiles": {
            "SYNTH-RECOVERY-003": {"failure_names": ["check_blacklist"]},
            "SYNTH-BOUNDARY-004": {"available_amount": "1500000"},
        },
        "allowlist": ["get_customer_profile", "get_credit_exposure", "check_blacklist"],
    }
    _write_json(ROOT / "fixtures" / "tools" / "tools-v1.json", tools)
    return len(specs) + len(demo_specs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic evaluation fixtures.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals" / "credit-review-v1" / "cases",
        help="Offline evaluation case root",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite generated fixture files")
    args = parser.parse_args()
    if not args.force and any(args.output.glob("*/manifest.json")):
        raise SystemExit("Fixtures already exist; use --force to regenerate them.")
    print(f"generated_cases={generate(args.output, force=args.force)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
