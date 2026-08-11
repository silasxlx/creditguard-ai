from langgraph.checkpoint.memory import MemorySaver

from app.workflow import CreditReviewState, build_graph, invoke_config


def test_graph_reaches_report_human_gate() -> None:
    graph = build_graph(MemorySaver())
    state: CreditReviewState = {
        "case_id": "case-1",
        "run_id": "run-1",
        "thread_id": "run-1",
        "trace_id": "trace-1",
        "workflow_version": "credit-review-1.0.0",
        "rule_pack_version": "1.0.0",
        "policy_pack_version": "synthetic-v1",
        "policy_index_version": "mock",
        "prompt_versions": {},
        "model_profile": {"provider": "mock"},
        "stage": "queued",
        "document_version_ids": [],
        "snapshot_refs": {},
        "conflict_ids": [],
        "decision_refs": [],
        "retry_count": 0,
        "needs_fact_review": False,
    }
    result = graph.invoke(state, config=invoke_config("run-1"))
    assert result["stage"] == "render_report"
    assert result["snapshot_refs"]["report"] == "mock-report-v1"


def test_graph_fact_gate_is_conditional() -> None:
    graph = build_graph(MemorySaver())
    state: CreditReviewState = {
        "case_id": "case-1",
        "run_id": "run-2",
        "thread_id": "run-2",
        "trace_id": "trace-2",
        "workflow_version": "credit-review-1.0.0",
        "rule_pack_version": "1.0.0",
        "policy_pack_version": "synthetic-v1",
        "policy_index_version": "mock",
        "prompt_versions": {},
        "model_profile": {"provider": "mock"},
        "stage": "queued",
        "document_version_ids": [],
        "snapshot_refs": {},
        "conflict_ids": [],
        "decision_refs": [],
        "retry_count": 0,
        "needs_fact_review": True,
    }
    result = graph.invoke(state, config=invoke_config("run-2"))
    assert result["stage"] == "detect_conflicts"
