from __future__ import annotations

from typing import cast

from app.models import ReviewRun
from app.report_service import build_report_payload, build_risk_payload


def _run_stub():
    from types import SimpleNamespace

    return SimpleNamespace(
        id="run-report-1",
        case_id="case-report-1",
        policy_index_version="index-v1",
    )


def test_risk_evidence_validator_isolates_unsupported_claims() -> None:
    facts = {
        "fields": {
            "F08": {
                "candidates": [{"evidence_id": "fact-evidence-1", "selected": True}],
                "selected_value": 48,
            }
        }
    }
    retrieval = {"hits": [], "by_rule": {}}
    tools = {"tools": {}}
    rules = {
        "summary_outcome": "NON_COMPLIANT",
        "results": [
            {
                "rule_id": "R07",
                "rule_name": "申请期限不超过36个月",
                "status": "FAIL",
                "message": "期限超过36个月上限。",
                "evidence_refs": ["not-in-current-run"],
            }
        ],
        "rule_pack_version": "1.0.0",
    }
    risks = build_risk_payload(facts, retrieval, tools, rules)
    assert risks["risks"][0]["evidence_status"] == "UNSUPPORTED"
    assert risks["unsupported_claims"]
    report = build_report_payload(
        cast(ReviewRun, _run_stub()), facts, retrieval, tools, rules, risks
    )
    assert report["unsupported_claims"]
    assert "UNSUPPORTED" in report["markdown"]


def test_report_template_escapes_untrusted_fact_markup() -> None:
    facts = {
        "fields": {
            "F01": {
                "field_name": "企业名称",
                "selected_value": "<script>alert(1)</script>",
                "candidates": [{"evidence_id": "fact-1", "selected": True}],
            }
        }
    }
    rules = {"summary_outcome": "PASS", "results": [], "rule_pack_version": "1.0.0"}
    report = build_report_payload(
        cast(ReviewRun, _run_stub()),
        facts,
        {"hits": []},
        {"tools": {}},
        rules,
        {"summary_outcome": "PASS", "risks": [], "unsupported_claims": []},
    )
    assert "<script>" not in report["markdown"]
    assert "&lt;script&gt;" in report["markdown"]
