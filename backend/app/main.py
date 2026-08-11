from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, Query, UploadFile, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db, init_business_db
from .demo import SCENARIOS, create_demo_scenario, demo_response_payload
from .errors import ServiceError
from .fact_service import get_fact_view, submit_fact_review
from .models import DocumentType, ReviewRun
from .report_service import get_report_view, submit_report_review
from .review_service import get_review_results as fetch_review_results
from .schemas import (
    CaseCreateRequest,
    CaseDetailResponse,
    CaseListResponse,
    CaseResponse,
    DemoScenarioResponse,
    DocumentListResponse,
    DocumentResponse,
    FactReviewRequest,
    FactReviewView,
    ReportResponse,
    ReportReviewRequest,
    RetryRequest,
    ReviewResultsResponse,
    RunCreateRequest,
    RunResponse,
)
from .security import require_role
from .service import (
    create_case,
    create_run,
    get_case,
    get_run,
    list_cases,
    list_documents,
    retry_run,
    save_document,
    to_run_response,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_business_db()
    yield


app = FastAPI(
    title="CreditGuard AI",
    version="0.1.0",
    description="AI-assisted credit compliance review for synthetic corporate lending cases.",
    lifespan=lifespan,
)


@app.exception_handler(ServiceError)
def service_error_handler(request, exc: ServiceError) -> JSONResponse:
    trace_id = str(uuid.uuid4())
    payload = {
        "type": f"https://creditguard.local/problems/{exc.code.lower()}",
        "title": exc.title,
        "status": exc.status,
        "detail": exc.detail,
        "instance": str(request.url.path),
        "code": exc.code,
        "trace_id": trace_id,
    }
    return JSONResponse(
        status_code=exc.status, content=payload, media_type="application/problem+json"
    )


def _limit(value: int) -> int:
    if value < 1 or value > 100:
        raise ServiceError("INVALID_LIMIT", "limit must be between 1 and 100.", 400)
    return value


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "creditguard-api", "version": app.version}


@app.post(
    "/api/v1/cases",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["cases"],
)
def post_case(
    payload: CaseCreateRequest,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")] = "",
) -> CaseResponse:
    user = require_role(demo_user_id, "RM")
    if not idempotency_key:
        raise ServiceError(
            "MISSING_IDEMPOTENCY_KEY", "Idempotency-Key is required for writes.", 400
        )
    return CaseResponse.model_validate(create_case(db, payload, user.user_id, idempotency_key))


@app.get("/api/v1/cases", response_model=CaseListResponse, tags=["cases"])
def get_cases(
    cursor: str | None = None,
    limit: int = Query(default=20),
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
) -> CaseListResponse:
    require_role(demo_user_id, "RM", "REVIEWER")
    rows, next_cursor = list_cases(db, cursor, _limit(limit))
    return CaseListResponse(
        items=[CaseResponse.model_validate(row) for row in rows], next_cursor=next_cursor
    )


@app.get("/api/v1/cases/{case_id}", response_model=CaseDetailResponse, tags=["cases"])
def get_case_detail(
    case_id: str,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
) -> CaseDetailResponse:
    require_role(demo_user_id, "RM", "REVIEWER")
    case = get_case(db, case_id)
    documents, _ = list_documents(db, case_id, None, 100)
    runs = []
    for run in (
        db.query(ReviewRun)
        .filter(ReviewRun.case_id == case_id)
        .order_by(ReviewRun.created_at.desc())
        .all()
    ):
        runs.append(to_run_response(run))
    return CaseDetailResponse(
        **CaseResponse.model_validate(case).model_dump(),
        documents=[DocumentResponse.model_validate(row) for row in documents],
        runs=runs,
    )


@app.post(
    "/api/v1/cases/{case_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def post_document(
    case_id: str,
    document_type: Annotated[DocumentType, Form()],
    file: Annotated[UploadFile, File()],
    replaces_document_id: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")] = "",
) -> DocumentResponse:
    user = require_role(demo_user_id, "RM")
    if not idempotency_key:
        raise ServiceError(
            "MISSING_IDEMPOTENCY_KEY", "Idempotency-Key is required for writes.", 400
        )
    content = await file.read()
    document = save_document(
        db,
        case_id=case_id,
        document_type=document_type,
        filename=file.filename or "unnamed",
        mime=file.content_type or "application/octet-stream",
        content=content,
        actor=user.user_id,
        idempotency_key=idempotency_key,
        replaces_document_id=replaces_document_id,
    )
    return DocumentResponse.model_validate(document)


@app.get(
    "/api/v1/cases/{case_id}/documents", response_model=DocumentListResponse, tags=["documents"]
)
def get_case_documents(
    case_id: str,
    cursor: str | None = None,
    limit: int = Query(default=20),
    active_only: bool = False,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
) -> DocumentListResponse:
    require_role(demo_user_id, "RM", "REVIEWER")
    rows, next_cursor = list_documents(db, case_id, cursor, _limit(limit))
    if active_only:
        rows = [row for row in rows if row.active]
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(row) for row in rows], next_cursor=next_cursor
    )


@app.post(
    "/api/v1/cases/{case_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["runs"],
)
def post_run(
    case_id: str,
    payload: RunCreateRequest,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")] = "",
) -> RunResponse:
    user = require_role(demo_user_id, "RM")
    if not idempotency_key:
        raise ServiceError(
            "MISSING_IDEMPOTENCY_KEY", "Idempotency-Key is required for writes.", 400
        )
    return to_run_response(create_run(db, case_id, payload, user.user_id, idempotency_key))


@app.get("/api/v1/runs/{run_id}", response_model=RunResponse, tags=["runs"])
def get_run_status(
    run_id: str,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
) -> RunResponse:
    require_role(demo_user_id, "RM", "REVIEWER")
    return to_run_response(get_run(db, run_id))


@app.post(
    "/api/v1/runs/{run_id}/retry",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["runs"],
)
def post_retry(
    run_id: str,
    payload: RetryRequest,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")] = "",
) -> RunResponse:
    user = require_role(demo_user_id, "RM", "REVIEWER")
    if not idempotency_key:
        raise ServiceError(
            "MISSING_IDEMPOTENCY_KEY", "Idempotency-Key is required for writes.", 400
        )
    return to_run_response(retry_run(db, run_id, user.user_id, idempotency_key))


def _not_ready() -> None:
    raise ServiceError(
        "SKELETON_NOT_IMPLEMENTED",
        "This contract is reserved for the next implementation stage.",
        501,
        "Not implemented",
    )


@app.get("/api/v1/runs/{run_id}/facts", tags=["review"])
def get_facts(
    run_id: str,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
) -> FactReviewView:
    require_role(demo_user_id, "REVIEWER")
    get_run(db, run_id)
    return get_fact_view(db, run_id)


@app.post("/api/v1/runs/{run_id}/fact-review", response_model=RunResponse, tags=["review"])
def post_fact_review(
    run_id: str,
    payload: FactReviewRequest,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")] = "",
) -> RunResponse:
    require_role(demo_user_id, "REVIEWER")
    if not idempotency_key:
        raise ServiceError(
            "MISSING_IDEMPOTENCY_KEY", "Idempotency-Key is required for writes.", 400
        )
    run = get_run(db, run_id)
    return to_run_response(
        submit_fact_review(db, run, payload, demo_user_id or "", idempotency_key)
    )


@app.get(
    "/api/v1/runs/{run_id}/review-results",
    response_model=ReviewResultsResponse,
    tags=["review"],
)
def get_review_results(
    run_id: str,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
) -> ReviewResultsResponse:
    require_role(demo_user_id, "REVIEWER")
    get_run(db, run_id)
    try:
        return ReviewResultsResponse.model_validate(fetch_review_results(db, run_id))
    except ValueError as exc:
        raise ServiceError("REVIEW_RESULTS_NOT_READY", str(exc), 409) from exc


@app.get("/api/v1/runs/{run_id}/report", tags=["report"])
def get_report(
    run_id: str,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
) -> ReportResponse:
    user = require_role(demo_user_id, "RM", "REVIEWER")
    get_run(db, run_id)
    return get_report_view(db, run_id, user.role)


@app.post(
    "/api/v1/runs/{run_id}/report-review",
    response_model=RunResponse,
    tags=["report"],
)
def post_report_review(
    run_id: str,
    payload: ReportReviewRequest,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")] = "",
) -> RunResponse:
    user = require_role(demo_user_id, "REVIEWER")
    if not idempotency_key:
        raise ServiceError(
            "MISSING_IDEMPOTENCY_KEY", "Idempotency-Key is required for writes.", 400
        )
    run = get_run(db, run_id)
    return to_run_response(submit_report_review(db, run, payload, user.user_id, idempotency_key))


@app.get("/api/v1/runs/{run_id}/report/export", tags=["report"])
def export_report(
    run_id: str,
    format: str = Query(default="markdown"),
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
) -> Response:
    user = require_role(demo_user_id, "RM", "REVIEWER")
    if format != "markdown":
        raise ServiceError("INVALID_EXPORT_FORMAT", "Only markdown export is supported.", 400)
    get_run(db, run_id)
    report = get_report_view(db, run_id, user.role)
    return Response(
        content=report.markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="credit-review-{run_id}.md"'},
    )


def post_demo_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    demo_user_id: Annotated[str | None, Header(alias="X-Demo-User-Id")] = None,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")] = "",
) -> JSONResponse:
    user = require_role(demo_user_id, "RM")
    if not idempotency_key:
        raise ServiceError(
            "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required for demo scenarios.", 400
        )
    if scenario_id not in SCENARIOS:
        raise ServiceError("DEMO_SCENARIO_NOT_FOUND", "The demo scenario does not exist.", 404)
    case, run, document_ids, created = create_demo_scenario(
        db, scenario_id, user.user_id, idempotency_key
    )
    payload = DemoScenarioResponse(
        **demo_response_payload(scenario_id, case, run, document_ids, created)
    ).model_dump(mode="json")
    return JSONResponse(status_code=201 if created else 200, content=payload)


if get_settings().demo_mode:
    app.add_api_route(
        "/api/v1/demo/scenarios/{scenario_id}",
        post_demo_scenario,
        response_model=DemoScenarioResponse,
        status_code=status.HTTP_201_CREATED,
        methods=["POST"],
        tags=["demo"],
    )
