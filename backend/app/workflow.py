from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


class CreditReviewState(TypedDict, total=False):
    case_id: str
    run_id: str
    thread_id: str
    trace_id: str
    workflow_version: str
    rule_pack_version: str
    policy_pack_version: str
    policy_index_version: str
    prompt_versions: dict[str, str]
    model_profile: dict[str, str]
    stage: str
    document_version_ids: list[str]
    snapshot_refs: dict[str, str]
    conflict_ids: list[str]
    pending_review: dict[str, Any] | None
    decision_refs: list[str]
    retry_count: int
    error_code: str | None
    pause_reason: str | None
    needs_fact_review: bool


PROGRESS = {
    "load_run": 2,
    "parse_documents": 20,
    "extract_facts": 35,
    "normalize_validate_facts": 45,
    "detect_conflicts": 50,
    "retrieve_policies": 65,
    "tools_metrics_rules": 80,
    "synthesize_validate_risks": 88,
    "render_report": 95,
    "completed": 100,
}


def _stage(state: CreditReviewState, name: str, **extra: Any) -> CreditReviewState:
    return {"stage": name, **extra, "progress_percent": PROGRESS.get(name, 0)}  # type: ignore[return-value]


def load_run(state: CreditReviewState) -> CreditReviewState:
    return _stage(state, "load_run")


def parse_documents(state: CreditReviewState) -> CreditReviewState:
    return _stage(state, "parse_documents")


def extract_facts(state: CreditReviewState) -> CreditReviewState:
    return _stage(
        state,
        "extract_facts",
        snapshot_refs={**state.get("snapshot_refs", {}), "fact": "mock-fact-v1"},
    )


def normalize_validate_facts(state: CreditReviewState) -> CreditReviewState:
    return _stage(state, "normalize_validate_facts")


def detect_conflicts(state: CreditReviewState) -> CreditReviewState:
    return _stage(
        state,
        "detect_conflicts",
        conflict_ids=["mock-conflict-001"] if state.get("needs_fact_review") else [],
    )


def route_fact_review(state: CreditReviewState) -> str:
    return "fact_review" if state.get("needs_fact_review") else "retrieve_policies"


def fact_review(state: CreditReviewState) -> CreditReviewState:
    decision = interrupt(
        {
            "gate": "FACT_REVIEW",
            "run_id": state.get("run_id", ""),
            "expected_snapshot_version": 1,
            "conflict_ids": state.get("conflict_ids", []),
            "allowed_actions": ["SELECT_SOURCE", "CORRECT_VALUE", "REQUEST_RESUBMISSION"],
        }
    )
    return _stage(state, "detect_conflicts", pending_review=None, decision_refs=[str(decision)])


def retrieve_policies(state: CreditReviewState) -> CreditReviewState:
    snapshot_refs = dict(state.get("snapshot_refs", {}))
    snapshot_refs.setdefault("retrieval", "pending")
    return _stage(
        state,
        "retrieve_policies",
        snapshot_refs=snapshot_refs,
    )


def tools_metrics_rules(state: CreditReviewState) -> CreditReviewState:
    snapshot_refs = dict(state.get("snapshot_refs", {}))
    snapshot_refs.setdefault("tool", "pending")
    snapshot_refs.setdefault("rule", "pending")
    return _stage(
        state,
        "tools_metrics_rules",
        snapshot_refs=snapshot_refs,
    )


def synthesize_validate_risks(state: CreditReviewState) -> CreditReviewState:
    snapshot_refs = dict(state.get("snapshot_refs", {}))
    snapshot_refs.setdefault("risk", "pending")
    return _stage(state, "synthesize_validate_risks", snapshot_refs=snapshot_refs)


def render_report(state: CreditReviewState) -> CreditReviewState:
    snapshot_refs = dict(state.get("snapshot_refs", {}))
    snapshot_refs.setdefault("report", "mock-report-v1")
    return _stage(
        state,
        "render_report",
        snapshot_refs=snapshot_refs,
    )


def report_review(state: CreditReviewState) -> CreditReviewState:
    decision = interrupt(
        {
            "gate": "REPORT_REVIEW",
            "run_id": state.get("run_id", ""),
            "expected_snapshot_version": 1,
            "report_ref": state.get("snapshot_refs", {}).get("report"),
            "allowed_actions": ["CONFIRM_DRAFT", "RETURN_FOR_RERUN"],
        }
    )
    if isinstance(decision, dict) and decision.get("action") == "RETURN_FOR_RERUN":
        return _stage(state, "returned", pause_reason=decision.get("reason"))
    return _stage(state, "completed")


def build_graph(checkpointer: Any):
    graph = StateGraph(CreditReviewState)
    graph.add_node("load_run", load_run)
    graph.add_node("parse_documents", parse_documents)
    graph.add_node("extract_facts", extract_facts)
    graph.add_node("normalize_validate_facts", normalize_validate_facts)
    graph.add_node("detect_conflicts", detect_conflicts)
    graph.add_node("fact_review", fact_review)
    graph.add_node("retrieve_policies", retrieve_policies)
    graph.add_node("tools_metrics_rules", tools_metrics_rules)
    graph.add_node("synthesize_validate_risks", synthesize_validate_risks)
    graph.add_node("render_report", render_report)
    graph.add_node("report_review", report_review)
    graph.add_edge(START, "load_run")
    graph.add_edge("load_run", "parse_documents")
    graph.add_edge("parse_documents", "extract_facts")
    graph.add_edge("extract_facts", "normalize_validate_facts")
    graph.add_edge("normalize_validate_facts", "detect_conflicts")
    graph.add_conditional_edges(
        "detect_conflicts",
        route_fact_review,
        {"fact_review": "fact_review", "retrieve_policies": "retrieve_policies"},
    )
    graph.add_edge("fact_review", "retrieve_policies")
    graph.add_edge("retrieve_policies", "tools_metrics_rules")
    graph.add_edge("tools_metrics_rules", "synthesize_validate_risks")
    graph.add_edge("synthesize_validate_risks", "render_report")
    graph.add_edge("render_report", "report_review")
    graph.add_edge("report_review", END)
    return graph.compile(checkpointer=checkpointer)


def build_checkpointer(path: Path, allow_memory: bool = False):
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path), check_same_thread=False)
        return SqliteSaver(connection)
    except ImportError as exc:
        if allow_memory:
            from langgraph.checkpoint.memory import MemorySaver

            return MemorySaver()
        raise RuntimeError(
            "langgraph-checkpoint-sqlite is required for normal runtime; "
            "set CREDIT_REVIEW_ALLOW_MEMORY_CHECKPOINT=true only for tests."
        ) from exc


def invoke_config(thread_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": thread_id}}


__all__ = [
    "CreditReviewState",
    "PROGRESS",
    "build_checkpointer",
    "build_graph",
    "invoke_config",
]
