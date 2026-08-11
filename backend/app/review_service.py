from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import CreditCase, Document, ReviewRun, Snapshot, SnapshotKind
from .report_service import build_report_payload, build_risk_payload
from .retrieval import (
    DashScopeEmbeddingProvider,
    DashScopeReranker,
    HashEmbeddingProvider,
    LexicalReranker,
    PolicyIndex,
    build_policy_index,
    persist_policy_index,
)
from .rules import RuleEngine, RuleEvaluationContext, load_rule_pack
from .tools import ReadOnlyToolRegistry, call_required_tools


@dataclass(frozen=True)
class ReviewCoreResult:
    fact_snapshot_id: str
    retrieval_payload: dict[str, Any]
    tool_payload: dict[str, Any]
    rule_payload: dict[str, Any]
    risk_payload: dict[str, Any]
    report_payload: dict[str, Any]


def _latest_snapshot(db: Session, run_id: str, kind: SnapshotKind) -> Snapshot:
    snapshot = db.scalar(
        select(Snapshot)
        .where(Snapshot.run_id == run_id, Snapshot.kind == kind)
        .order_by(Snapshot.version.desc())
    )
    if not snapshot:
        raise ValueError(f"Missing {kind.value} snapshot for Run {run_id}")
    return snapshot


def _snapshot_version(db: Session, run_id: str, kind: SnapshotKind) -> int:
    return (
        int(
            db.scalar(
                select(func.max(Snapshot.version)).where(
                    Snapshot.run_id == run_id, Snapshot.kind == kind
                )
            )
            or 0
        )
        + 1
    )


def _hash_payload(payload: dict[str, Any]) -> str:
    import hashlib
    import json

    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _save_snapshot(
    db: Session, run_id: str, kind: SnapshotKind, payload: dict[str, Any]
) -> Snapshot:
    snapshot = Snapshot(
        run_id=run_id,
        kind=kind,
        version=_snapshot_version(db, run_id, kind),
        payload_json=payload,
        payload_hash=_hash_payload(payload),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _build_index(settings: Any) -> PolicyIndex:
    embedder: Any = HashEmbeddingProvider()
    reranker: Any = LexicalReranker()
    if settings.use_remote_models and settings.dashscope_api_key:
        embedder = DashScopeEmbeddingProvider(
            settings.dashscope_base_url, settings.dashscope_api_key
        )
        reranker = DashScopeReranker(settings.dashscope_base_url, settings.dashscope_api_key)
    return build_policy_index(
        Path(settings.policy_root),
        policy_pack_version="synthetic-v1",
        embedder=embedder,
        reranker=reranker,
    )


def evaluate_review_core(db: Session, run: ReviewRun) -> ReviewCoreResult:
    settings = get_settings()
    fact_snapshot = _latest_snapshot(db, run.id, SnapshotKind.FACT)
    fact_payload = fact_snapshot.payload_json
    if fact_payload.get("requires_review"):
        raise ValueError("Cannot execute rules while fact review is unresolved")
    case = db.get(CreditCase, run.case_id)
    if not case:
        raise ValueError("Case for Run does not exist")
    documents = [
        {
            "id": document.id,
            "document_type": document.document_type.value,
            "status": document.status.value,
            "version": document.version,
        }
        for document in db.scalars(
            select(Document).where(Document.id.in_(run.document_version_ids))
        )
    ]
    index = _build_index(settings)
    persist_policy_index(db, index, Path(settings.policy_root))
    rule_pack = load_rule_pack(Path(settings.rule_pack_path))
    existing_rule = db.scalar(
        select(Snapshot)
        .where(Snapshot.run_id == run.id, Snapshot.kind == SnapshotKind.RULE)
        .order_by(Snapshot.version.desc())
    )
    if existing_rule and existing_rule.payload_json.get("rule_pack_hash") != rule_pack.sha256:
        raise ValueError("Rule pack version has a different hash for this Run")
    retrieval_by_rule: dict[str, list[dict[str, Any]]] = {}
    retrieval_hits: list[dict[str, Any]] = []
    for definition in rule_pack.rules:
        hits = index.search(definition.query_template, definition.rule_id, top_k=5)
        serialized = [hit.to_dict() for hit in hits]
        retrieval_by_rule[definition.rule_id] = serialized
        retrieval_hits.extend(serialized)
    retrieval_payload = {
        "schema_version": "1.0",
        "producer": {"type": "retrieval", "version": "poc-1.0.0"},
        "policy_pack_version": index.policy_pack_version,
        "index_manifest_hash": index.manifest_hash,
        "embedding_model": index.embedder.model_name,
        "reranker_model": index.reranker.model_name,
        "bm25_top_k": 30,
        "dense_top_k": 30,
        "rrf_k": 60,
        "rerank_top_k": 5,
        "hits": retrieval_hits,
        "by_rule": retrieval_by_rule,
    }
    tools = call_required_tools(ReadOnlyToolRegistry(), case.customer_key, run.id)
    tool_payload = {
        "schema_version": "1.0",
        "tools": tools,
        "allowlist": ["get_customer_profile", "get_credit_exposure", "check_blacklist"],
    }
    context = RuleEvaluationContext(
        facts=fact_payload,
        documents=documents,
        review_date=case.review_date,
        tools=tools,
        retrieval=retrieval_by_rule,
        conflict_ids=[
            str(conflict.get("conflict_id"))
            for conflict in fact_payload.get("conflicts", [])
            if conflict.get("selected_value") is None
        ],
    )
    engine = RuleEngine(rule_pack)
    results = engine.evaluate(context)
    rule_payload = {
        "schema_version": "1.0",
        "rule_pack_version": rule_pack.version,
        "rule_pack_hash": rule_pack.sha256,
        "summary_outcome": engine.summarize(results),
        "results": results,
        "financial_metrics": {
            "leverage_ratio": next(
                (
                    item.get("details", {}).get("ratio_percent")
                    for item in results
                    if item["rule_id"] == "R09"
                ),
                None,
            ),
            "current_ratio": next(
                (
                    item.get("details", {}).get("ratio")
                    for item in results
                    if item["rule_id"] == "R10"
                ),
                None,
            ),
        },
    }
    run.policy_pack_version = index.policy_pack_version
    run.policy_index_version = index.manifest_hash
    run.rule_pack_version = rule_pack.version
    risk_payload = build_risk_payload(
        fact_payload,
        retrieval_payload,
        tool_payload,
        rule_payload,
    )
    report_payload = build_report_payload(
        run,
        fact_payload,
        retrieval_payload,
        tool_payload,
        rule_payload,
        risk_payload,
    )
    retrieval_snapshot = _save_snapshot(db, run.id, SnapshotKind.RETRIEVAL, retrieval_payload)
    tool_snapshot = _save_snapshot(db, run.id, SnapshotKind.TOOL, tool_payload)
    rule_snapshot = _save_snapshot(db, run.id, SnapshotKind.RULE, rule_payload)
    risk_snapshot = _save_snapshot(db, run.id, SnapshotKind.RISK, risk_payload)
    report_snapshot = _save_snapshot(db, run.id, SnapshotKind.REPORT, report_payload)
    return ReviewCoreResult(
        fact_snapshot_id=fact_snapshot.id,
        retrieval_payload={**retrieval_payload, "snapshot_id": retrieval_snapshot.id},
        tool_payload={**tool_payload, "snapshot_id": tool_snapshot.id},
        rule_payload={**rule_payload, "snapshot_id": rule_snapshot.id},
        risk_payload={**risk_payload, "snapshot_id": risk_snapshot.id},
        report_payload={**report_payload, "snapshot_id": report_snapshot.id},
    )


def get_review_results(db: Session, run_id: str) -> dict[str, Any]:
    run = db.get(ReviewRun, run_id)
    if not run:
        raise ValueError("Run does not exist")
    facts = _latest_snapshot(db, run_id, SnapshotKind.FACT).payload_json
    rule = _latest_snapshot(db, run_id, SnapshotKind.RULE).payload_json
    retrieval = _latest_snapshot(db, run_id, SnapshotKind.RETRIEVAL).payload_json
    tools = _latest_snapshot(db, run_id, SnapshotKind.TOOL).payload_json
    risks = _latest_snapshot(db, run_id, SnapshotKind.RISK).payload_json
    report = _latest_snapshot(db, run_id, SnapshotKind.REPORT)
    report_payload = report.payload_json
    return {
        "run_id": run_id,
        "summary_outcome": rule.get("summary_outcome"),
        "fact_snapshot_version": _latest_snapshot(db, run_id, SnapshotKind.FACT).version,
        "facts": facts,
        "rules": rule.get("results", []),
        "financial_metrics": rule.get("financial_metrics", {}),
        "retrieval": retrieval,
        "tools": tools,
        "risks": risks.get("risks", []),
        "unsupported_claims": risks.get("unsupported_claims", []),
        "report_status": report_payload.get("report_status", "AWAITING_REVIEW"),
        "report_snapshot_version": report.version,
    }


__all__ = ["ReviewCoreResult", "evaluate_review_core", "get_review_results"]
