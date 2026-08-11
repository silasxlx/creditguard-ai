from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal, engine, init_business_db
from app.main import app
from app.models import Base, Document
from app.tools import ReadOnlyToolRegistry


@pytest.fixture(autouse=True)
def clean_database() -> None:
    init_business_db()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _headers(user: str = "demo-rm", key: str = "security-key") -> dict[str, str]:
    return {"X-Demo-User-Id": user, "Idempotency-Key": key}


def _pdf_bytes() -> bytes:
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "synthetic security fixture", fontsize=9)
    return document.tobytes()


def test_tool_registry_rejects_non_allowlisted_tool() -> None:
    with pytest.raises(ValueError, match="not allowlisted"):
        ReadOnlyToolRegistry().call("execute_sql", "SYNTH-001", "security-run")


def test_upload_normalizes_filename_and_rejects_macro_extension() -> None:
    client = TestClient(app)
    case_response = client.post(
        "/api/v1/cases",
        headers=_headers(key="security-case"),
        json={
            "case_no": "SECURITY-001",
            "customer_name": "合成安全企业",
            "customer_key": "SYNTH-SECURITY-001",
            "review_date": "2026-08-10",
        },
    )
    assert case_response.status_code == 201, case_response.text
    case_id = case_response.json()["id"]
    upload = client.post(
        f"/api/v1/cases/{case_id}/documents",
        headers=_headers(key="security-upload"),
        data={"document_type": "BUSINESS_LICENSE"},
        files={"file": ("..\\..\\evidence.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    with SessionLocal() as db:
        document = db.query(Document).one()
        assert document.original_filename == "evidence.pdf"
        assert ".." not in document.storage_key
        assert document.storage_key.startswith(f"{case_id}/")

    rejected = client.post(
        f"/api/v1/cases/{case_id}/documents",
        headers=_headers(key="security-macro"),
        data={"document_type": "CREDIT_APPLICATION"},
        files={
            "file": (
                "macro.docm",
                BytesIO(b"synthetic macro fixture"),
                "application/vnd.ms-word.document.macroEnabled.12",
            )
        },
    )
    assert rejected.status_code == 415
    assert rejected.json()["code"] == "INVALID_FILE_TYPE"


def test_security_scan_has_no_repository_findings() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.security_scan import scan

    assert scan() == []
