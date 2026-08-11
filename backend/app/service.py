from __future__ import annotations

import base64
import binascii
import hashlib
import json
import mimetypes
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .errors import ServiceError
from .models import (
    AuditEvent,
    CreditCase,
    Document,
    DocumentStatus,
    DocumentType,
    IdempotencyRecord,
    JobStatus,
    ReviewRun,
    RunStatus,
    TaskJob,
)
from .schemas import CaseCreateRequest, RunCreateRequest, RunResponse

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}
MIME_BY_EXTENSION = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    },
}
REQUIRED_DOCUMENT_TYPES = set(DocumentType)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(payload)


def _cursor_offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise ServiceError("INVALID_CURSOR", "The cursor is invalid.", 400) from exc


def _next_cursor(offset: int, size: int, limit: int) -> str | None:
    if size < limit:
        return None
    return base64.urlsafe_b64encode(str(offset + size).encode()).decode()


def _idempotent_resource(
    db: Session, scope: str, key: str, request_hash: str, resource_type: str
) -> str | None:
    existing = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.idempotency_key == key,
        )
    )
    if existing:
        if existing.request_hash != request_hash or existing.resource_type != resource_type:
            raise ServiceError(
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used with a different request.",
                409,
                "Idempotency conflict",
            )
        return existing.resource_id
    return None


def _save_idempotency(
    db: Session, scope: str, key: str, request_hash: str, resource_type: str, resource_id: str
) -> None:
    db.add(
        IdempotencyRecord(
            scope=scope,
            idempotency_key=key,
            request_hash=request_hash,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    )


def _audit(
    db: Session, event_type: str, actor: str, case_id: str | None = None, run_id: str | None = None
) -> None:
    db.add(AuditEvent(event_type=event_type, actor=actor, case_id=case_id, run_id=run_id))


def create_case(
    db: Session, payload: CaseCreateRequest, actor: str, idempotency_key: str
) -> CreditCase:
    request_hash = _sha256_json(payload.model_dump(mode="json"))
    scope = "POST:/api/v1/cases"
    existing_id = _idempotent_resource(db, scope, idempotency_key, request_hash, "case")
    if existing_id:
        case = db.get(CreditCase, existing_id)
        if case:
            return case
    if db.scalar(select(CreditCase).where(CreditCase.case_no == payload.case_no)):
        raise ServiceError("CASE_NO_EXISTS", "case_no already exists.", 409, "Case conflict")
    case = CreditCase(**payload.model_dump(), created_by=actor)
    db.add(case)
    db.flush()
    _save_idempotency(db, scope, idempotency_key, request_hash, "case", case.id)
    _audit(db, "CASE_CREATED", actor, case_id=case.id)
    db.commit()
    db.refresh(case)
    return case


def list_cases(db: Session, cursor: str | None, limit: int) -> tuple[list[CreditCase], str | None]:
    offset = _cursor_offset(cursor)
    rows = list(
        db.scalars(
            select(CreditCase)
            .order_by(CreditCase.created_at.desc(), CreditCase.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return rows, _next_cursor(offset, len(rows), limit)


def get_case(db: Session, case_id: str) -> CreditCase:
    case = db.get(CreditCase, case_id)
    if not case:
        raise ServiceError("CASE_NOT_FOUND", "The case does not exist.", 404, "Not found")
    return case


def list_documents(
    db: Session, case_id: str, cursor: str | None, limit: int
) -> tuple[list[Document], str | None]:
    get_case(db, case_id)
    offset = _cursor_offset(cursor)
    rows = list(
        db.scalars(
            select(Document)
            .where(Document.case_id == case_id)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return rows, _next_cursor(offset, len(rows), limit)


def save_document(
    db: Session,
    case_id: str,
    document_type: DocumentType,
    filename: str,
    mime: str,
    content: bytes,
    actor: str,
    idempotency_key: str,
    replaces_document_id: str | None = None,
) -> Document:
    case = get_case(db, case_id)
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ServiceError(
            "INVALID_FILE_TYPE", "Only PDF, DOCX and XLSX are accepted.", 415, "Invalid file"
        )
    if mime and mime not in MIME_BY_EXTENSION[suffix]:
        raise ServiceError(
            "INVALID_FILE_TYPE",
            "The MIME type does not match the file extension.",
            415,
            "Invalid file",
        )
    if not content:
        raise ServiceError("EMPTY_FILE", "The uploaded file is empty.", 400, "Invalid file")
    if len(content) > 20 * 1024 * 1024:
        raise ServiceError(
            "FILE_TOO_LARGE", "A single file cannot exceed 20MB.", 413, "File too large"
        )

    request_hash = _sha256_json(
        {
            "case_id": case_id,
            "document_type": document_type.value,
            "filename": filename,
            "content_hash": _sha256_bytes(content),
            "replaces_document_id": replaces_document_id,
        }
    )
    scope = f"POST:/api/v1/cases/{case_id}/documents"
    existing_id = _idempotent_resource(db, scope, idempotency_key, request_hash, "document")
    if existing_id:
        document = db.get(Document, existing_id)
        if document:
            return document

    replacement = None
    if replaces_document_id:
        replacement = db.get(Document, replaces_document_id)
        if (
            not replacement
            or replacement.case_id != case_id
            or replacement.document_type != document_type
        ):
            raise ServiceError(
                "INVALID_REPLACEMENT",
                "The replacement document is invalid.",
                409,
                "Document conflict",
            )
    active_count = (
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.case_id == case_id, Document.active.is_(True))
        )
        or 0
    )
    if active_count >= 10 and not replacement:
        raise ServiceError(
            "CASE_FILE_LIMIT",
            "A case cannot have more than 10 active materials.",
            409,
            "Case limit",
        )

    latest_version = (
        db.scalar(
            select(func.max(Document.version)).where(
                Document.case_id == case_id,
                Document.document_type == document_type,
            )
        )
        or 0
    )
    if replacement:
        replacement.active = False
    storage_key = f"{case_id}/{uuid.uuid4().hex}{suffix}"
    settings = get_settings()
    path = settings.storage_path / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    document = Document(
        case_id=case.id,
        document_type=document_type,
        version=latest_version + 1,
        active=True,
        original_filename=Path(filename).name,
        content_hash=_sha256_bytes(content),
        mime=mime or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        size_bytes=len(content),
        storage_key=storage_key,
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    case.version += 1
    db.flush()
    _save_idempotency(db, scope, idempotency_key, request_hash, "document", document.id)
    _audit(db, "DOCUMENT_UPLOADED", actor, case_id=case.id)
    db.commit()
    db.refresh(document)
    return document


def _manifest_hash(db: Session, documents: list[Document]) -> str:
    return _sha256_json(
        [
            {
                "id": document.id,
                "type": document.document_type.value,
                "version": document.version,
                "content_hash": document.content_hash,
            }
            for document in sorted(documents, key=lambda item: item.id)
        ]
    )


def allowed_actions(run: ReviewRun) -> list[str]:
    if run.status is RunStatus.PAUSED_RETRYABLE:
        return ["RETRY"]
    if run.status is RunStatus.WAITING_FACT_REVIEW:
        return ["FACT_REVIEW"]
    if run.status is RunStatus.WAITING_REPORT_REVIEW:
        return ["REPORT_REVIEW"]
    if run.status is RunStatus.QUEUED:
        return ["VIEW_PROGRESS"]
    return []


def to_run_response(run: ReviewRun) -> RunResponse:
    return RunResponse(
        id=run.id,
        case_id=run.case_id,
        status=run.status,
        stage=run.stage,
        progress_percent=run.progress_percent,
        waiting_gate=run.waiting_gate,
        retryable=run.retryable,
        pause_reason=run.pause_reason,
        error_code=run.error_code,
        input_document_version_ids=run.document_version_ids,
        workflow_version=run.workflow_version,
        rule_pack_version=run.rule_pack_version,
        policy_pack_version=run.policy_pack_version,
        policy_index_version=run.policy_index_version,
        prompt_versions=run.prompt_versions or {},
        model_profile=run.model_profile or {},
        allowed_actions=allowed_actions(run),
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def create_run(
    db: Session, case_id: str, payload: RunCreateRequest, actor: str, idempotency_key: str
) -> ReviewRun:
    case = get_case(db, case_id)
    if payload.expected_case_version != case.version:
        raise ServiceError(
            "STALE_CASE_VERSION", "The case version is stale.", 409, "Case version conflict"
        )
    if len(payload.document_version_ids) != 4:
        raise ServiceError(
            "REQUIRED_MATERIAL_SET", "Exactly four required material versions are needed.", 400
        )
    documents = list(
        db.scalars(
            select(Document).where(
                Document.case_id == case_id,
                Document.id.in_(payload.document_version_ids),
                Document.active.is_(True),
            )
        )
    )
    if (
        len(documents) != 4
        or {document.document_type for document in documents} != REQUIRED_DOCUMENT_TYPES
    ):
        raise ServiceError(
            "REQUIRED_MATERIAL_SET", "One active version of each required material is needed.", 400
        )
    if any(
        document.status not in {DocumentStatus.UPLOADED, DocumentStatus.PARSED}
        for document in documents
    ):
        raise ServiceError(
            "MATERIAL_NOT_READY", "All selected materials must be uploaded or parsed.", 409
        )

    request_hash = _sha256_json(payload.model_dump(mode="json"))
    scope = f"POST:/api/v1/cases/{case_id}/runs"
    existing_id = _idempotent_resource(db, scope, idempotency_key, request_hash, "run")
    if existing_id:
        run = db.get(ReviewRun, existing_id)
        if run:
            return run

    run = ReviewRun(
        case_id=case_id,
        status=RunStatus.QUEUED,
        stage="queued",
        progress_percent=0,
        retryable=False,
        input_manifest_hash=_manifest_hash(db, documents),
        document_version_ids=payload.document_version_ids,
        prompt_versions={"fact_extraction": "prompt-fact-v1"},
        model_profile={"provider": "mock", "requested_model": "mock-qwen3.7-flash"},
    )
    db.add(run)
    db.flush()
    db.add(TaskJob(run_id=run.id, idempotency_key=f"run:{run.id}:initial"))
    _save_idempotency(db, scope, idempotency_key, request_hash, "run", run.id)
    _audit(db, "RUN_CREATED", actor, case_id=case_id, run_id=run.id)
    db.commit()
    db.refresh(run)
    return run


def get_run(db: Session, run_id: str) -> ReviewRun:
    run = db.get(ReviewRun, run_id)
    if not run:
        raise ServiceError("RUN_NOT_FOUND", "The review Run does not exist.", 404, "Not found")
    return run


def retry_run(db: Session, run_id: str, actor: str, idempotency_key: str) -> ReviewRun:
    run = get_run(db, run_id)
    if run.status is not RunStatus.PAUSED_RETRYABLE:
        raise ServiceError("RUN_NOT_RETRYABLE", "Only PAUSED_RETRYABLE runs can be retried.", 409)
    request_hash = _sha256_json(
        {"run_id": run_id, "expected_status": RunStatus.PAUSED_RETRYABLE.value}
    )
    scope = f"POST:/api/v1/runs/{run_id}/retry"
    existing_id = _idempotent_resource(db, scope, idempotency_key, request_hash, "run")
    if existing_id:
        existing = db.get(ReviewRun, existing_id)
        if existing:
            return existing
    task = db.scalar(select(TaskJob).where(TaskJob.run_id == run_id))
    if not task:
        raise ServiceError("TASK_NOT_FOUND", "The Run task does not exist.", 500, "Task error")
    task.status = JobStatus.PENDING
    task.owner = None
    task.leased_until = None
    run.status = RunStatus.QUEUED
    run.stage = "queued"
    run.retryable = False
    run.pause_reason = None
    run.error_code = None
    _save_idempotency(db, scope, idempotency_key, request_hash, "run", run.id)
    _audit(db, "RUN_RETRY_REQUESTED", actor, case_id=run.case_id, run_id=run.id)
    db.commit()
    db.refresh(run)
    return run


def claim_job(
    db: Session, worker_id: str, now: datetime | None = None
) -> tuple[TaskJob, ReviewRun] | None:
    now = now or datetime.now(UTC)
    task = db.scalar(
        select(TaskJob)
        .where(
            TaskJob.status.in_([JobStatus.PENDING, JobStatus.RETRYABLE]),
            (TaskJob.leased_until.is_(None) | (TaskJob.leased_until < now)),
        )
        .order_by(TaskJob.created_at.asc())
    )
    if not task:
        return None
    task.status = JobStatus.LEASED
    task.owner = worker_id
    task.attempt += 1
    task.leased_until = now.replace(microsecond=0) + timedelta(seconds=60)
    run = db.get(ReviewRun, task.run_id)
    if not run:
        task.status = JobStatus.FAILED_FINAL
        db.commit()
        return None
    run.status = RunStatus.RUNNING
    run.stage = "worker_claimed"
    run.progress_percent = max(run.progress_percent, 2)
    db.commit()
    db.refresh(task)
    db.refresh(run)
    return task, run
