from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import DocumentStatus, DocumentType, RunStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        protected_namespaces=(),
    )


class ProblemDetails(ApiModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    trace_id: str


class CaseCreateRequest(ApiModel):
    case_no: str = Field(min_length=1, max_length=64)
    customer_name: str = Field(min_length=1, max_length=200)
    customer_key: str = Field(min_length=1, max_length=100)
    review_date: date


class CaseResponse(ApiModel):
    id: str
    case_no: str
    customer_name: str
    customer_key: str
    review_date: date
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class CaseDetailResponse(CaseResponse):
    documents: list[DocumentResponse] = Field(default_factory=list)
    runs: list[RunResponse] = Field(default_factory=list)


class DocumentResponse(ApiModel):
    id: str
    case_id: str
    document_type: DocumentType
    version: int
    active: bool
    original_filename: str
    content_hash: str
    mime: str
    size_bytes: int
    storage_key: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


class RunCreateRequest(ApiModel):
    document_version_ids: list[str] = Field(min_length=4, max_length=10)
    expected_case_version: int = Field(ge=1)

    @field_validator("document_version_ids")
    @classmethod
    def unique_document_ids(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("document_version_ids must be unique")
        return value


class RunResponse(ApiModel):
    id: str
    case_id: str
    status: RunStatus
    stage: str
    progress_percent: int = Field(ge=0, le=100)
    waiting_gate: str | None = None
    retryable: bool
    pause_reason: str | None = None
    error_code: str | None = None
    input_document_version_ids: list[str]
    workflow_version: str
    rule_pack_version: str
    policy_pack_version: str
    policy_index_version: str
    prompt_versions: dict[str, str]
    model_profile: dict[str, str]
    allowed_actions: list[str]
    created_at: datetime
    updated_at: datetime


class RetryRequest(ApiModel):
    expected_status: RunStatus = RunStatus.PAUSED_RETRYABLE

    @field_validator("expected_status")
    @classmethod
    def only_retryable(cls, value: RunStatus) -> RunStatus:
        if value is not RunStatus.PAUSED_RETRYABLE:
            raise ValueError("expected_status must be PAUSED_RETRYABLE")
        return value


class Pagination(ApiModel):
    items: list[Any]
    next_cursor: str | None = None


class CaseListResponse(ApiModel):
    items: list[CaseResponse]
    next_cursor: str | None = None


class DemoScenarioResponse(ApiModel):
    scenario_id: str
    case_id: str
    run_id: str
    case_version: int
    input_document_version_ids: list[str]
    run_status: RunStatus
    created: bool


class DocumentListResponse(ApiModel):
    items: list[DocumentResponse]
    next_cursor: str | None = None


class RunListResponse(ApiModel):
    items: list[RunResponse]
    next_cursor: str | None = None


class GateName(str, Enum):
    FACT_REVIEW = "FACT_REVIEW"
    REPORT_REVIEW = "REPORT_REVIEW"


class FactReviewAction(str, Enum):
    SELECT_SOURCE = "SELECT_SOURCE"
    CORRECT_VALUE = "CORRECT_VALUE"
    REQUEST_RESUBMISSION = "REQUEST_RESUBMISSION"


class FactCandidateResponse(ApiModel):
    field: str
    field_name: str
    value_type: str
    raw_value: str
    normalized_value: Any
    document_version_id: str
    evidence_id: str
    locator: dict[str, object]
    source: str
    selected: bool = False
    validation_reasons: list[str] | None = None


class FactFieldResponse(ApiModel):
    field: str
    field_name: str
    value_type: str
    candidates: list[FactCandidateResponse]
    selected_value: Any = None
    requires_review: bool


class FactConflictResponse(ApiModel):
    conflict_id: str
    field: str
    field_name: str
    comparison: str
    candidates: list[FactCandidateResponse]
    difference: dict[str, str] | None = None
    material: bool
    selected_value: Any = None


class FactReviewView(ApiModel):
    run_id: str
    snapshot_version: int
    fields: dict[str, FactFieldResponse]
    missing_fields: list[str]
    conflicts: list[FactConflictResponse]
    requires_review: bool
    allowed_actions: list[FactReviewAction]


class FactDecision(ApiModel):
    conflict_id: str
    action: FactReviewAction
    selected_evidence_id: str | None = None
    corrected_value: Any | None = None
    reason: str = ""

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        return value.strip()


class FactReviewRequest(ApiModel):
    expected_snapshot_version: int = Field(ge=1)
    decisions: list[FactDecision] = Field(min_length=1)


class ReviewResultsResponse(ApiModel):
    run_id: str
    summary_outcome: str
    fact_snapshot_version: int
    facts: dict[str, Any]
    rules: list[dict[str, Any]]
    financial_metrics: dict[str, Any]
    retrieval: dict[str, Any]
    tools: dict[str, Any]
    unsupported_claims: list[dict[str, Any]]
    risks: list[dict[str, Any]] = Field(default_factory=list)
    report_status: str = "AWAITING_REVIEW"
    report_snapshot_version: int | None = None


class ReportReviewAction(str, Enum):
    CONFIRM_DRAFT = "CONFIRM_DRAFT"
    RETURN_FOR_RERUN = "RETURN_FOR_RERUN"


class ReportReviewRequest(ApiModel):
    expected_snapshot_version: int = Field(ge=1)
    action: ReportReviewAction
    reason: str = ""

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        return value.strip()


class ReportResponse(ApiModel):
    run_id: str
    snapshot_version: int
    report_status: str
    report_hash: str
    summary_outcome: str
    markdown: str
    risks: list[dict[str, Any]]
    unsupported_claims: list[dict[str, Any]]
    evidence_refs: list[str]
    allowed_actions: list[str]
