from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402

REQUIRED_PATHS = {
    "/health",
    "/api/v1/cases",
    "/api/v1/cases/{case_id}",
    "/api/v1/cases/{case_id}/documents",
    "/api/v1/cases/{case_id}/runs",
    "/api/v1/runs/{run_id}",
    "/api/v1/runs/{run_id}/facts",
    "/api/v1/runs/{run_id}/fact-review",
    "/api/v1/runs/{run_id}/review-results",
    "/api/v1/runs/{run_id}/report",
    "/api/v1/runs/{run_id}/report-review",
    "/api/v1/runs/{run_id}/report/export",
}
REQUIRED_SCHEMAS = {
    "RunResponse": {"id", "status", "allowed_actions"},
    "ReportResponse": {"run_id", "report_status", "markdown", "allowed_actions"},
}


def check() -> list[str]:
    document = app.openapi()
    errors: list[str] = []
    missing_paths = sorted(REQUIRED_PATHS - set(document.get("paths", {})))
    if missing_paths:
        errors.append(f"missing paths: {', '.join(missing_paths)}")
    schemas = document.get("components", {}).get("schemas", {})
    for schema_name, fields in REQUIRED_SCHEMAS.items():
        actual = set(schemas.get(schema_name, {}).get("properties", {}))
        missing = sorted(fields - actual)
        if missing:
            errors.append(f"{schema_name} missing fields: {', '.join(missing)}")
    return errors


def main() -> int:
    errors = check()
    payload = {"status": "PASS" if not errors else "FAIL", "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
