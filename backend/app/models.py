from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class DocumentType(str, enum.Enum):
    BUSINESS_LICENSE = "BUSINESS_LICENSE"
    CREDIT_APPLICATION = "CREDIT_APPLICATION"
    DUE_DILIGENCE = "DUE_DILIGENCE"
    FINANCIAL_STATEMENTS = "FINANCIAL_STATEMENTS"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    PARSED = "PARSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"


class RunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FACT_REVIEW = "WAITING_FACT_REVIEW"
    WAITING_REPORT_REVIEW = "WAITING_REPORT_REVIEW"
    PAUSED_RETRYABLE = "PAUSED_RETRYABLE"
    COMPLETED = "COMPLETED"
    RETURNED = "RETURNED"
    FAILED_FINAL = "FAILED_FINAL"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    LEASED = "LEASED"
    RETRYABLE = "RETRYABLE"
    SUCCEEDED = "SUCCEEDED"
    FAILED_FINAL = "FAILED_FINAL"


class SnapshotKind(str, enum.Enum):
    PARSE = "PARSE"
    FACT = "FACT"
    CONFLICT = "CONFLICT"
    RETRIEVAL = "RETRIEVAL"
    TOOL = "TOOL"
    RULE = "RULE"
    RISK = "RISK"
    REPORT = "REPORT"


class CreditCase(Base):
    __tablename__ = "credit_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(200))
    customer_key: Mapped[str] = mapped_column(String(100), index=True)
    review_date: Mapped[date] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("case_id", "document_type", "version", name="uq_document_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("credit_cases.id"), index=True)
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), index=True)
    version: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    mime: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.UPLOADED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ReviewRun(Base):
    __tablename__ = "review_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("credit_cases.id"), index=True)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.QUEUED, index=True)
    stage: Mapped[str] = mapped_column(String(64), default="queued")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    waiting_gate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False)
    pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    input_manifest_hash: Mapped[str] = mapped_column(String(64))
    document_version_ids: Mapped[list[str]] = mapped_column(JSON)
    workflow_version: Mapped[str] = mapped_column(String(40), default="credit-review-1.0.0")
    rule_pack_version: Mapped[str] = mapped_column(String(40), default="1.0.0")
    policy_pack_version: Mapped[str] = mapped_column(String(80), default="synthetic-v1")
    policy_index_version: Mapped[str] = mapped_column(String(80), default="not-built")
    prompt_versions: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    model_profile: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class TaskJob(Base):
    __tablename__ = "task_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("review_runs.id"), unique=True, index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, index=True
    )
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (UniqueConstraint("run_id", "kind", "version", name="uq_snapshot_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("review_runs.id"), index=True)
    kind: Mapped[SnapshotKind] = mapped_column(Enum(SnapshotKind))
    version: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0")
    payload_json: Mapped[dict] = mapped_column(JSON)
    payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor: Mapped[str] = mapped_column(String(100))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("scope", "idempotency_key", name="uq_idempotency_scope_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scope: Mapped[str] = mapped_column(String(200))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HumanDecision(Base):
    __tablename__ = "human_decisions"
    __table_args__ = (
        UniqueConstraint("run_id", "gate", "idempotency_key", name="uq_human_decision_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("review_runs.id"), index=True)
    gate: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(50))
    before_version: Mapped[int] = mapped_column(Integer)
    after_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    actor: Mapped[str] = mapped_column(String(100))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    __table_args__ = (
        UniqueConstraint("policy_pack_version", "source_hash", name="uq_policy_source_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    policy_pack_version: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_filename: Mapped[str] = mapped_column(String(255))
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"
    __table_args__ = (UniqueConstraint("chunk_id", name="uq_policy_chunk_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    policy_document_id: Mapped[str] = mapped_column(ForeignKey("policy_documents.id"), index=True)
    policy_pack_version: Mapped[str] = mapped_column(String(80), index=True)
    chunk_id: Mapped[str] = mapped_column(String(64), index=True)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    section_path: Mapped[list[str]] = mapped_column(JSON, default=list)
    text: Mapped[str] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(64))
    locator: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
