from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .errors import ServiceError
from .models import (
    AuditEvent,
    HumanDecision,
    IdempotencyRecord,
    JobStatus,
    ReviewRun,
    RunStatus,
    Snapshot,
    SnapshotKind,
    TaskJob,
)
from .schemas import ReportResponse, ReportReviewAction, ReportReviewRequest


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _latest_snapshot(db: Session, run_id: str, kind: SnapshotKind) -> Snapshot:
    snapshot = db.scalar(
        select(Snapshot)
        .where(Snapshot.run_id == run_id, Snapshot.kind == kind)
        .order_by(Snapshot.version.desc())
    )
    if not snapshot:
        raise ServiceError("REPORT_NOT_READY", f"The {kind.value} snapshot is not ready.", 409)
    return snapshot


def _next_snapshot_version(db: Session, run_id: str, kind: SnapshotKind) -> int:
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


def _save_snapshot(db: Session, run_id: str, payload: dict[str, Any]) -> Snapshot:
    snapshot = Snapshot(
        run_id=run_id,
        kind=SnapshotKind.REPORT,
        version=_next_snapshot_version(db, run_id, SnapshotKind.REPORT),
        payload_json=payload,
        payload_hash=_hash_payload(payload),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _valid_evidence_ids(
    facts: dict[str, Any], retrieval: dict[str, Any], tools: dict[str, Any]
) -> set[str]:
    evidence: set[str] = set()
    for field in facts.get("fields", {}).values():
        for candidate in field.get("candidates", []):
            if candidate.get("evidence_id"):
                evidence.add(str(candidate["evidence_id"]))
    for hit in retrieval.get("hits", []):
        if hit.get("selected") and hit.get("chunk_id"):
            evidence.add(str(hit["chunk_id"]))
    for name in tools.get("tools", {}):
        evidence.add(f"tool:{name}")
    return evidence


def build_risk_payload(
    facts: dict[str, Any],
    retrieval: dict[str, Any],
    tools: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    valid_evidence = _valid_evidence_ids(facts, retrieval, tools)
    risks: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    for result in rules.get("results", []):
        status = result.get("status")
        if status == "PASS":
            continue
        refs = [str(ref) for ref in result.get("evidence_refs", [])]
        invalid_refs = [ref for ref in refs if ref not in valid_evidence]
        evidence_status = "SUPPORTED" if refs and not invalid_refs else "UNSUPPORTED"
        risk = {
            "risk_id": f"RISK-{result.get('rule_id')}",
            "rule_id": result.get("rule_id"),
            "severity": "HIGH" if status in {"FAIL", "NEEDS_REVIEW"} else "MEDIUM",
            "title": result.get("rule_name", "规则风险"),
            "explanation": result.get("message", ""),
            "evidence_refs": refs,
            "invalid_evidence_refs": invalid_refs,
            "evidence_status": evidence_status,
            "source": "deterministic_rule_engine",
        }
        risks.append(risk)
        if evidence_status == "UNSUPPORTED":
            unsupported.append(
                {
                    "claim_id": risk["risk_id"],
                    "claim": risk["explanation"],
                    "reason": "风险项缺少当前Run可验证证据。",
                }
            )
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary_outcome": rules.get("summary_outcome"),
        "risks": risks,
        "unsupported_claims": unsupported,
        "valid_evidence_count": len(valid_evidence),
    }


def _safe_text(value: Any) -> str:
    text = str(value if value is not None else "")
    return (
        text.replace("\r", " ")
        .replace("\n", " ")
        .replace("|", "\\|")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .strip()
    )


def build_report_payload(
    run: ReviewRun,
    facts: dict[str, Any],
    retrieval: dict[str, Any],
    tools: dict[str, Any],
    rules: dict[str, Any],
    risks: dict[str, Any],
) -> dict[str, Any]:
    lines = [
        "# 授信智能合规审查报告",
        "",
        f"- Run ID：`{run.id}`",
        f"- 案件 ID：`{run.case_id}`",
        f"- 规则包版本：`{_safe_text(rules.get('rule_pack_version'))}`",
        f"- 制度索引版本：`{_safe_text(run.policy_index_version)}`",
        "",
        "## 1. 汇总结论",
        "",
        f"**审查状态：{_safe_text(rules.get('summary_outcome'))}**",
        "",
        "> 本报告为AI辅助合规审查草稿，需Reviewer确认，不构成授信审批、额度决策或放款指令。",
        "",
        "## 2. 关键事实",
        "",
        "| 字段 | 采用值 | 证据 |",
        "|---|---|---|",
    ]
    for field_id, field in facts.get("fields", {}).items():
        evidence = ", ".join(
            str(candidate.get("evidence_id"))
            for candidate in field.get("candidates", [])
            if candidate.get("selected")
        )
        lines.append(
            f"| {_safe_text(field.get('field_name', field_id))} | {_safe_text(field.get('selected_value'))} | `{_safe_text(evidence)}` |"
        )
    lines.extend(["", "## 3. 规则结果", "", "| 规则 | 结果 | 说明 |", "|---|---|---|"])
    for result in rules.get("results", []):
        lines.append(
            f"| {_safe_text(result.get('rule_id'))} {_safe_text(result.get('rule_name'))} | **{_safe_text(result.get('status'))}** | {_safe_text(result.get('message'))} |"
        )
    lines.extend(["", "## 4. 风险项", ""])
    if risks.get("risks"):
        lines.extend(["| 风险 | 等级 | 证据状态 | 说明 |", "|---|---|---|---|"])
        for risk in risks["risks"]:
            lines.append(
                f"| {_safe_text(risk.get('risk_id'))} {_safe_text(risk.get('title'))} | {_safe_text(risk.get('severity'))} | {_safe_text(risk.get('evidence_status'))} | {_safe_text(risk.get('explanation'))} |"
            )
    else:
        lines.append("未发现规则风险项。")
    lines.extend(["", "## 5. 制度依据", ""])
    selected_hits = [hit for hit in retrieval.get("hits", []) if hit.get("selected")]
    for hit in selected_hits[:20]:
        section = " / ".join(str(item) for item in hit.get("section_path", []))
        lines.append(
            f"- `{_safe_text(hit.get('rule_id'))}`：{_safe_text(section)}；chunk=`{_safe_text(hit.get('chunk_id'))}`；quote_hash=`{_safe_text(hit.get('quote_hash'))}`"
        )
    lines.extend(["", "## 6. 工具状态", ""])
    for name, result in tools.get("tools", {}).items():
        lines.append(f"- `{_safe_text(name)}`：{_safe_text(result.get('status'))}")
    lines.extend(["", "## 7. 局限和待办", ""])
    if risks.get("summary_outcome") == "REVIEW_BLOCKED":
        lines.append("- 存在需要人工处理或重试的不确定项，报告不得确认。")
    if risks.get("unsupported_claims"):
        lines.append("- 存在UNSUPPORTED风险项，已从正式结论中隔离。")
    lines.append("- 本PoC不执行最终授信审批、额度决策或放款。")
    markdown = "\n".join(lines) + "\n"
    report_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return {
        "schema_version": "1.0",
        "report_status": "AWAITING_REVIEW",
        "report_hash": report_hash,
        "summary_outcome": rules.get("summary_outcome"),
        "markdown": markdown,
        "risks": risks.get("risks", []),
        "unsupported_claims": risks.get("unsupported_claims", []),
        "evidence_refs": sorted(
            {
                str(ref)
                for risk in risks.get("risks", [])
                for ref in risk.get("evidence_refs", [])
                if ref
            }
        ),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def get_report_view(db: Session, run_id: str, role: str) -> ReportResponse:
    snapshot = _latest_snapshot(db, run_id, SnapshotKind.REPORT)
    payload = snapshot.payload_json
    if role == "RM" and payload.get("report_status") != "CONFIRMED":
        raise ServiceError(
            "REPORT_NOT_CONFIRMED",
            "The full report is available to RM only after Reviewer confirmation.",
            403,
            "Forbidden",
        )
    return ReportResponse(
        run_id=run_id,
        snapshot_version=snapshot.version,
        report_status=payload.get("report_status", "AWAITING_REVIEW"),
        report_hash=payload.get("report_hash", ""),
        summary_outcome=payload.get("summary_outcome", "REVIEW_BLOCKED"),
        markdown=payload.get("markdown", ""),
        risks=payload.get("risks", []),
        unsupported_claims=payload.get("unsupported_claims", []),
        evidence_refs=payload.get("evidence_refs", []),
        allowed_actions=(
            ["CONFIRM_DRAFT", "RETURN_FOR_RERUN"]
            if payload.get("report_status") == "AWAITING_REVIEW"
            else []
        ),
    )


def submit_report_review(
    db: Session,
    run: ReviewRun,
    request: ReportReviewRequest,
    actor: str,
    idempotency_key: str,
) -> ReviewRun:
    request_hash = _hash_payload(request.model_dump(mode="json"))
    scope = f"POST:/api/v1/runs/{run.id}/report-review"
    existing = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.request_hash != request_hash:
            raise ServiceError(
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used with a different request.",
                409,
                "Idempotency conflict",
            )
        existing_run = db.get(ReviewRun, existing.resource_id)
        if existing_run:
            return existing_run
        raise ServiceError("RUN_NOT_FOUND", "The review Run does not exist.", 404, "Not found")
    if run.status is not RunStatus.WAITING_REPORT_REVIEW:
        raise ServiceError(
            "INVALID_STATE_TRANSITION", "The Run is not waiting for report review.", 409
        )
    current = _latest_snapshot(db, run.id, SnapshotKind.REPORT)
    if current.version != request.expected_snapshot_version:
        raise ServiceError("STALE_SNAPSHOT", "The report snapshot version is stale.", 409)
    payload = dict(current.payload_json)
    if payload.get("report_status") != "AWAITING_REVIEW":
        raise ServiceError("REPORT_ALREADY_REVIEWED", "The report has already been reviewed.", 409)
    task = db.scalar(select(TaskJob).where(TaskJob.run_id == run.id))
    if not task:
        raise ServiceError("TASK_NOT_FOUND", "The Run task does not exist.", 500, "Task error")
    if request.action is ReportReviewAction.CONFIRM_DRAFT:
        if payload.get("summary_outcome") == "REVIEW_BLOCKED":
            raise ServiceError(
                "REPORT_BLOCKED", "Resolve NEEDS_REVIEW items before confirmation.", 409
            )
        if payload.get("unsupported_claims"):
            raise ServiceError(
                "REPORT_BLOCKED", "Unsupported claims cannot enter a confirmed report.", 409
            )
        next_status = "CONFIRMED"
        next_run_status = RunStatus.COMPLETED
        next_stage = "completed"
        next_gate = None
        next_progress = 100
    else:
        if not request.reason:
            raise ServiceError("REASON_REQUIRED", "A return reason is required.", 400)
        next_status = "RETURNED"
        next_run_status = RunStatus.RETURNED
        next_stage = "returned"
        next_gate = None
        next_progress = run.progress_percent
    next_payload = dict(payload)
    next_payload["report_status"] = next_status
    next_payload["reviewed_at"] = datetime.now(UTC).isoformat()
    next_payload["reviewed_by"] = actor
    next_payload["review_reason"] = request.reason or "Reviewer confirmed the draft."
    next_snapshot = _save_snapshot(db, run.id, next_payload)
    db.add(
        HumanDecision(
            run_id=run.id,
            gate="REPORT_REVIEW",
            action=request.action.value,
            before_version=current.version,
            after_version=next_snapshot.version,
            reason=next_payload["review_reason"],
            payload_json=request.model_dump(mode="json"),
            actor=actor,
            idempotency_key=idempotency_key,
        )
    )
    db.add(
        IdempotencyRecord(
            scope=scope,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            resource_type="run",
            resource_id=run.id,
        )
    )
    run.status = next_run_status
    run.stage = next_stage
    run.progress_percent = next_progress
    run.waiting_gate = next_gate
    run.retryable = False
    task.status = JobStatus.SUCCEEDED
    db.add(
        AuditEvent(
            case_id=run.case_id,
            run_id=run.id,
            event_type="REPORT_REVIEW_SUBMITTED",
            actor=actor,
            metadata_json={
                "action": request.action.value,
                "before_version": current.version,
                "after_version": next_snapshot.version,
            },
        )
    )
    db.commit()
    db.refresh(run)
    return run


__all__ = [
    "build_report_payload",
    "build_risk_payload",
    "get_report_view",
    "submit_report_review",
]
