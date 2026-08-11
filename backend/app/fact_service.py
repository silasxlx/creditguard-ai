from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .errors import ServiceError
from .facts import FACT_DEFINITIONS, build_fact_payload, normalize_value
from .models import (
    AuditEvent,
    Document,
    DocumentStatus,
    HumanDecision,
    IdempotencyRecord,
    JobStatus,
    ReviewRun,
    RunStatus,
    Snapshot,
    SnapshotKind,
    TaskJob,
)
from .parsing import MinerUHttpAdapter, ParsedDocument, parse_document
from .schemas import FactReviewAction, FactReviewRequest, FactReviewView


@dataclass
class MaterialFactResult:
    fact_payload: dict[str, Any]
    parse_payload: dict[str, Any]
    conflict_payload: dict[str, Any]
    requires_review: bool


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


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


def _save_snapshot(
    db: Session, run_id: str, kind: SnapshotKind, payload: dict[str, Any]
) -> Snapshot:
    snapshot = Snapshot(
        run_id=run_id,
        kind=kind,
        version=_next_snapshot_version(db, run_id, kind),
        payload_json=payload,
        payload_hash=_payload_hash(payload),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _serialize_parsed(parsed: ParsedDocument) -> dict[str, Any]:
    return {
        "document_version_id": parsed.document_version_id,
        "filename": parsed.filename,
        "quality": {
            "parser": parsed.quality.parser,
            "effective_characters": parsed.quality.effective_characters,
            "page_count": parsed.quality.page_count,
            "locatable_characters": parsed.quality.locatable_characters,
            "average_chars_per_page": parsed.quality.average_chars_per_page,
            "needs_mineru": parsed.quality.needs_mineru,
            "reasons": parsed.quality.reasons,
            "rejected": parsed.quality.rejected,
            "cache_missing": parsed.quality.cache_missing,
        },
        "blocks": [block.model_dump(mode="json") for block in parsed.blocks],
    }


def process_materials_and_facts(db: Session, run: ReviewRun) -> MaterialFactResult:
    parsed_documents: list[ParsedDocument] = []
    parse_payload: dict[str, Any] = {"schema_version": "1.0", "documents": []}
    requires_review = False
    settings = get_settings()
    mineru = (
        MinerUHttpAdapter(settings.mineru_base_url, settings.mineru_api_key)
        if settings.mineru_base_url and settings.mineru_api_key
        else None
    )
    for document_id in run.document_version_ids:
        document = db.get(Document, document_id)
        if not document or document.case_id != run.case_id:
            raise ServiceError("DOCUMENT_NOT_FOUND", "A Run input material does not exist.", 409)
        path = settings.storage_path / document.storage_key
        if not path.exists():
            document.status = DocumentStatus.NEEDS_REVIEW
            requires_review = True
            continue
        parsed = parse_document(
            document.id, path.read_bytes(), document.original_filename, mineru=mineru
        )
        parsed_documents.append(parsed)
        parse_payload["documents"].append(_serialize_parsed(parsed))
        if parsed.quality.rejected:
            document.status = DocumentStatus.REJECTED
            requires_review = True
        elif parsed.quality.needs_mineru or parsed.quality.cache_missing:
            document.status = DocumentStatus.NEEDS_REVIEW
            requires_review = True
        else:
            document.status = DocumentStatus.PARSED

    fact_payload = build_fact_payload(parsed_documents)
    conflict_payload = {
        "schema_version": "1.0",
        "conflicts": fact_payload["conflicts"],
        "requires_review": bool(
            any(conflict["material"] for conflict in fact_payload["conflicts"])
            or fact_payload["missing_fields"]
            or requires_review
        ),
    }
    fact_payload["requires_review"] = conflict_payload["requires_review"]
    _save_snapshot(db, run.id, SnapshotKind.PARSE, parse_payload)
    _save_snapshot(db, run.id, SnapshotKind.FACT, fact_payload)
    _save_snapshot(db, run.id, SnapshotKind.CONFLICT, conflict_payload)
    db.add(
        AuditEvent(
            case_id=run.case_id,
            run_id=run.id,
            event_type="MATERIAL_FACT_STAGE_COMPLETED",
            actor="worker",
            metadata_json={"requires_review": conflict_payload["requires_review"]},
        )
    )
    run.stage = "detect_conflicts"
    run.progress_percent = 50
    db.commit()
    return MaterialFactResult(
        fact_payload, parse_payload, conflict_payload, conflict_payload["requires_review"]
    )


def _latest_snapshot(db: Session, run_id: str, kind: SnapshotKind) -> Snapshot:
    snapshot = db.scalar(
        select(Snapshot)
        .where(Snapshot.run_id == run_id, Snapshot.kind == kind)
        .order_by(Snapshot.version.desc())
    )
    if not snapshot:
        raise ServiceError("FACT_SNAPSHOT_NOT_FOUND", "The Run has no fact snapshot.", 409)
    return snapshot


def get_fact_view(db: Session, run_id: str) -> FactReviewView:
    fact = _latest_snapshot(db, run_id, SnapshotKind.FACT)
    payload = fact.payload_json
    fields = payload.get("fields", {})
    conflicts = payload.get("conflicts", [])
    return FactReviewView(
        run_id=run_id,
        snapshot_version=fact.version,
        fields=fields,
        missing_fields=payload.get("missing_fields", []),
        conflicts=conflicts,
        requires_review=bool(payload.get("requires_review", False)),
        allowed_actions=[
            FactReviewAction.SELECT_SOURCE,
            FactReviewAction.CORRECT_VALUE,
            FactReviewAction.REQUEST_RESUBMISSION,
        ],
    )


def _find_conflict(payload: dict[str, Any], conflict_id: str) -> dict[str, Any]:
    for conflict in payload.get("conflicts", []):
        if conflict.get("conflict_id") == conflict_id:
            return conflict
    raise ServiceError(
        "CONFLICT_NOT_FOUND", "The conflict does not belong to this Run.", 404, "Conflict not found"
    )


def submit_fact_review(
    db: Session,
    run: ReviewRun,
    request: FactReviewRequest,
    actor: str,
    idempotency_key: str,
) -> ReviewRun:
    request_hash = _payload_hash(request.model_dump(mode="json"))
    scope = f"POST:/api/v1/runs/{run.id}/fact-review"
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
    if run.status is not RunStatus.WAITING_FACT_REVIEW:
        raise ServiceError(
            "INVALID_STATE_TRANSITION", "The Run is not waiting for fact review.", 409
        )
    current = _latest_snapshot(db, run.id, SnapshotKind.FACT)
    if request.expected_snapshot_version != current.version:
        raise ServiceError(
            "STALE_SNAPSHOT", "The fact snapshot version is stale.", 409, "Snapshot conflict"
        )
    payload = json.loads(json.dumps(current.payload_json, ensure_ascii=False))
    conflicts_by_id = {item["conflict_id"]: item for item in payload.get("conflicts", [])}
    decisions = {decision.conflict_id: decision for decision in request.decisions}
    material_conflicts = [item for item in conflicts_by_id.values() if item.get("material")]
    if not any(decision.action.value == "REQUEST_RESUBMISSION" for decision in request.decisions):
        missing = [
            item["conflict_id"]
            for item in material_conflicts
            if item["conflict_id"] not in decisions
        ]
        if missing:
            raise ServiceError(
                "INCOMPLETE_FACT_REVIEW", "Every material conflict needs a decision.", 400
            )

    task = db.scalar(select(TaskJob).where(TaskJob.run_id == run.id))
    if not task:
        raise ServiceError("TASK_NOT_FOUND", "The Run task does not exist.", 500, "Task error")

    for index, decision in enumerate(request.decisions):
        conflict = _find_conflict(payload, decision.conflict_id)
        field = conflict["field"]
        field_payload = payload["fields"][field]
        if decision.action.value == "REQUEST_RESUBMISSION":
            if not decision.reason:
                raise ServiceError("REASON_REQUIRED", "A resubmission reason is required.", 400)
            db.add(
                HumanDecision(
                    run_id=run.id,
                    gate="FACT_REVIEW",
                    action=decision.action.value,
                    before_version=current.version,
                    reason=decision.reason,
                    payload_json=decision.model_dump(mode="json"),
                    actor=actor,
                    idempotency_key=f"{idempotency_key}:{index}",
                )
            )
            run.status = RunStatus.RETURNED
            run.stage = "returned"
            run.waiting_gate = None
            run.retryable = False
            task.status = JobStatus.SUCCEEDED
            db.add(
                IdempotencyRecord(
                    scope=scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    resource_type="run",
                    resource_id=run.id,
                )
            )
            db.commit()
            return run
        if decision.action.value == "SELECT_SOURCE":
            if not decision.selected_evidence_id:
                raise ServiceError(
                    "EVIDENCE_REQUIRED", "SELECT_SOURCE requires selected_evidence_id.", 400
                )
            candidate = next(
                (
                    item
                    for item in conflict["candidates"]
                    if item["evidence_id"] == decision.selected_evidence_id
                ),
                None,
            )
            if not candidate:
                raise ServiceError(
                    "EVIDENCE_NOT_IN_CONFLICT",
                    "The evidence is not a candidate for this conflict.",
                    400,
                )
            field_payload["selected_value"] = candidate["normalized_value"]
            for item in field_payload["candidates"]:
                item["selected"] = item["evidence_id"] == decision.selected_evidence_id
        elif decision.action.value == "CORRECT_VALUE":
            if decision.corrected_value is None or not decision.reason:
                raise ServiceError(
                    "CORRECTION_REQUIRES_REASON", "A corrected value and reason are required.", 400
                )
            normalized, reasons = normalize_value(field, str(decision.corrected_value))
            if reasons:
                raise ServiceError("INVALID_CORRECTED_VALUE", ", ".join(reasons), 400)
            evidence_id = hashlib.sha256(
                f"manual|{run.id}|{field}|{current.version}".encode()
            ).hexdigest()
            manual = {
                "field": field,
                "field_name": FACT_DEFINITIONS[field]["name"],
                "value_type": FACT_DEFINITIONS[field]["type"],
                "raw_value": str(decision.corrected_value),
                "normalized_value": normalized,
                "document_version_id": "manual",
                "evidence_id": evidence_id,
                "locator": {"source": "human_decision"},
                "source": "Reviewer",
                "selected": True,
                "validation_reasons": [],
            }
            field_payload["candidates"].append(manual)
            field_payload["selected_value"] = normalized
        db.add(
            HumanDecision(
                run_id=run.id,
                gate="FACT_REVIEW",
                action=decision.action.value,
                before_version=current.version,
                reason=decision.reason or "选择材料来源值",
                payload_json=decision.model_dump(mode="json"),
                actor=actor,
                idempotency_key=f"{idempotency_key}:{index}",
            )
        )

    payload["requires_review"] = False
    for field_payload in payload["fields"].values():
        if field_payload.get("selected_value") is None:
            field_payload["requires_review"] = True
            payload["requires_review"] = True
    for conflict in payload.get("conflicts", []):
        conflict["selected_value"] = payload["fields"][conflict["field"]].get("selected_value")
    new_fact = _save_snapshot(db, run.id, SnapshotKind.FACT, payload)
    _save_snapshot(
        db,
        run.id,
        SnapshotKind.CONFLICT,
        {
            "schema_version": "1.0",
            "conflicts": payload.get("conflicts", []),
            "requires_review": payload["requires_review"],
        },
    )
    if payload["requires_review"]:
        raise ServiceError("FACT_REVIEW_INCOMPLETE", "Some required facts remain unresolved.", 400)
    from .review_service import evaluate_review_core

    evaluate_review_core(db, run)
    run.status = RunStatus.WAITING_REPORT_REVIEW
    run.stage = "render_report"
    run.progress_percent = 95
    run.waiting_gate = "REPORT_REVIEW"
    run.retryable = False
    task.status = JobStatus.SUCCEEDED
    db.add(
        IdempotencyRecord(
            scope=scope,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            resource_type="run",
            resource_id=run.id,
        )
    )
    db.add(
        AuditEvent(
            case_id=run.case_id,
            run_id=run.id,
            event_type="FACT_REVIEW_SUBMITTED",
            actor=actor,
            metadata_json={"before_version": current.version, "after_version": new_fact.version},
        )
    )
    db.commit()
    db.refresh(run)
    return run
