from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from app.retrieval import DashScopeReranker, build_policy_index
from app.rules import RuleEngine, RuleEvaluationContext, evaluate_rule, load_rule_pack
from app.tools import ReadOnlyToolRegistry, ToolProfile, call_required_tools


def _facts(term: int = 36, assets: str = "5000000", liabilities: str = "2000000") -> dict:
    values = {
        "F03": "2020-01-01",
        "F05": "制造业",
        "F06": "1000000",
        "F07": "CNY",
        "F08": term,
        "F09": "流动资金",
        "F10": assets,
        "F11": liabilities,
        "F12": "3000000",
        "F13": "1500000",
    }
    fields = {
        field: {
            "selected_value": value,
            "candidates": [
                {
                    "evidence_id": f"evidence-{field}",
                    "selected": True,
                }
            ],
        }
        for field, value in values.items()
    }
    return {"fields": fields, "conflicts": [], "requires_review": False}


def _context(term: int = 36, tools: dict | None = None) -> RuleEvaluationContext:
    selected_hit = {
        "chunk_id": "policy-chunk-r07",
        "selected": True,
    }
    return RuleEvaluationContext(
        facts=_facts(term=term),
        documents=[
            {"id": "doc-1", "document_type": kind, "status": "PARSED"}
            for kind in (
                "BUSINESS_LICENSE",
                "CREDIT_APPLICATION",
                "DUE_DILIGENCE",
                "FINANCIAL_STATEMENTS",
            )
        ],
        review_date=date(2026, 8, 10),
        tools=tools or call_required_tools(ReadOnlyToolRegistry(), "SYNTH-001", "run-1"),
        retrieval={rule_id: [selected_hit] for rule_id in ("R03", "R06", "R07")},
        conflict_ids=[],
    )


def test_policy_index_runs_bm25_dense_rrf_and_reranker_deterministically() -> None:
    root = Path("config/policies/synthetic-v1")
    first = build_policy_index(root)
    second = build_policy_index(root)
    assert len(first.chunks) == 18
    assert first.manifest_hash == second.manifest_hash
    hits = first.search("流动资金贷款期限不得超过36个月", "R07")
    assert 1 <= len(hits) <= 20
    assert sum(hit.selected for hit in hits) == min(5, len(hits))
    assert hits[0].bm25_rank == 1
    assert hits[0].dense_rank is not None
    assert hits[0].rrf_score == pytest.approx(
        sum(1 / (60 + rank) for rank in (hits[0].bm25_rank, hits[0].dense_rank) if rank is not None)
    )
    assert hits[0].rerank_rank == 1
    assert hits[0].locator["source_filename"] == "03-limit-and-tenor.md"


def test_rule_pack_has_ten_rules_and_enforces_boundaries() -> None:
    pack = load_rule_pack(Path("config/rules/rule-pack-v1.yaml"))
    assert pack.version == "1.0.0"
    assert [rule.rule_id for rule in pack.rules] == [f"R{i:02d}" for i in range(1, 11)]
    engine = RuleEngine(pack)
    results = engine.evaluate(_context(term=36))
    assert len(results) == 10
    assert engine.summarize(results) == "PASS"
    assert evaluate_rule(pack.rules[6], _context(term=37))["status"] == "FAIL"
    incomplete = _context()
    assert (
        evaluate_rule(pack.rules[0], replace(incomplete, documents=incomplete.documents[:-1]))[
            "status"
        ]
        == "FAIL"
    )
    assert evaluate_rule(pack.rules[8], _context())["details"]["ratio_percent"] == "40.0"
    assert evaluate_rule(pack.rules[9], _context())["details"]["ratio"] == "2"


def test_tool_failure_is_needs_review_and_unknown_rule_is_rejected(monkeypatch) -> None:
    profile = ToolProfile(customer_key="SYNTH-FAIL", failure_names=frozenset({"check_blacklist"}))
    tools = call_required_tools(
        ReadOnlyToolRegistry({"SYNTH-FAIL": profile}), "SYNTH-FAIL", "run-2"
    )
    pack = load_rule_pack(Path("config/rules/rule-pack-v1.yaml"))
    result = evaluate_rule(pack.rules[3], _context(tools=tools))
    assert result["status"] == "NEEDS_REVIEW"
    invalid_content = (
        b"version: '1.0.0'\nname: bad\n"
        b"allowed_operators: [eq, ne, gt, gte, lt, lte, in, not_in, is_present]\n"
        b"rules: [{id: R01, name: bad, predicate: eval, query_template: bad}]\n"
    )
    monkeypatch.setattr(type(Path("invalid.yaml")), "read_bytes", lambda _path: invalid_content)
    with pytest.raises(ValueError, match="Unknown rule predicate"):
        load_rule_pack(Path("invalid.yaml"))


def test_dashscope_reranker_uses_compatible_api_reranks_endpoint(monkeypatch) -> None:
    called: dict[str, object] = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"results": [{"index": 0, "relevance_score": 0.9}]}

    def fake_post(url: str, **kwargs: object) -> Response:
        called["url"] = url
        called["kwargs"] = kwargs
        return Response()

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)
    reranker = DashScopeReranker(
        "https://dashscope.aliyuncs.com/compatible-mode/v1", "synthetic-key"
    )
    assert reranker.rerank("期限", ["期限不得超过36个月"]) == [0.9]
    assert called["url"] == "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"
