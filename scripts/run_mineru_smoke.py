from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def run(output: Path, max_wait_seconds: int = 180) -> int:
    import httpx

    api_key = os.environ.get("CREDIT_REVIEW_MINERU_API_KEY") or os.environ.get("MINERU_API_KEY")
    if not api_key:
        print("MINERU_API_KEY is required for manual smoke", file=sys.stderr)
        return 2
    base_url = (
        os.environ.get("CREDIT_REVIEW_MINERU_BASE_URL")
        or os.environ.get("MINERU_BASE_URL")
        or "https://mineru.net/api/v4"
    ).rstrip("/")
    source_url = os.environ.get(
        "MINERU_SMOKE_SOURCE_URL",
        "https://cdn-mineru.openxlab.org.cn/demo/example.pdf",
    )
    result: dict[str, object] = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "endpoint_family": "mineru-v4-extract-task",
        "base_url": base_url,
        "source_url_hash": _sha256(source_url.encode("utf-8")),
        "secrets_recorded": False,
        "auth_configured": True,
        "states": [],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            submitted = client.post(
                f"{base_url}/extract/task",
                headers=headers,
                json={"url": source_url, "model_version": "vlm"},
            )
            submitted.raise_for_status()
            payload = submitted.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            task_id = data.get("task_id") if isinstance(data, dict) else None
            result["submit"] = {
                "http_status": submitted.status_code,
                "provider_code": payload.get("code") if isinstance(payload, dict) else None,
                "trace_id_present": bool(payload.get("trace_id")) if isinstance(payload, dict) else False,
                "task_id_present": bool(task_id),
            }
            if not task_id:
                result["status"] = "FAIL"
                result["error_type"] = "MISSING_TASK_ID"
                return _write_result(output, result, 1)
            deadline = time.monotonic() + max_wait_seconds
            while time.monotonic() < deadline:
                response = client.get(f"{base_url}/extract/task/{task_id}", headers=headers)
                response.raise_for_status()
                body = response.json()
                task_data = body.get("data") if isinstance(body, dict) else None
                state = str(task_data.get("state")) if isinstance(task_data, dict) else "UNKNOWN"
                result["states"].append(state)
                if state == "done":
                    result_url = None
                    result_kind = None
                    if isinstance(task_data, dict):
                        result_url = task_data.get("markdown_url") or task_data.get("full_zip_url")
                        result_kind = "markdown" if task_data.get("markdown_url") else "full_zip"
                    if not result_url:
                        result["status"] = "FAIL"
                        result["error_type"] = "MISSING_RESULT_URL"
                        return _write_result(output, result, 1)
                    result_response = client.get(str(result_url), timeout=30.0)
                    result_response.raise_for_status()
                    result["result"] = {
                        "kind": result_kind,
                        "http_status": result_response.status_code,
                        "content_length": len(result_response.content),
                        "content_sha256": _sha256(result_response.content),
                    }
                    result["status"] = "PASS"
                    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
                    return _write_result(output, result, 0)
                if state == "failed":
                    result["status"] = "FAIL"
                    result["error_type"] = "PROVIDER_TASK_FAILED"
                    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
                    return _write_result(output, result, 1)
                time.sleep(3)
            result["status"] = "TIMEOUT"
            result["error_type"] = "POLL_TIMEOUT"
    except Exception as exc:  # pragma: no cover - requires external service
        result["status"] = "FAIL"
        result["error_type"] = type(exc).__name__
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return _write_result(output, result, 1)


def _write_result(output: Path, result: dict[str, object], exit_code: int) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "states"}, ensure_ascii=False))
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual, synthetic MinerU v4 smoke test.")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts" / "external-smoke" / "mineru-result.json"
    )
    parser.add_argument("--max-wait-seconds", type=int, default=180)
    args = parser.parse_args()
    return run(args.output, args.max_wait_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
