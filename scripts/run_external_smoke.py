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
sys.path.insert(0, str(ROOT / "backend"))

from app.retrieval import DashScopeEmbeddingProvider, DashScopeReranker  # noqa: E402


def _prompt_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def run(output: Path) -> int:
    api_key = os.environ.get("CREDIT_REVIEW_DASHSCOPE_API_KEY") or os.environ.get(
        "DASHSCOPE_API_KEY"
    )
    if not api_key:
        print("DASHSCOPE_API_KEY is required for manual smoke", file=sys.stderr)
        return 2
    base_url = os.environ.get("CREDIT_REVIEW_DASHSCOPE_BASE_URL") or (
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    query = "流动资金贷款期限不得超过三十六个月"
    document = "一般流动资金贷款期限不得超过三十六个月，期限以整数月表示。"
    result: dict[str, object] = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "provider_region": "beijing",
        "prompt_hash": _prompt_hash(query),
        "secrets_recorded": False,
        "calls": [],
    }
    embedder = DashScopeEmbeddingProvider(base_url, api_key)
    reranker = DashScopeReranker(base_url, api_key)
    for name, action in (
        ("embedding", lambda: embedder.embed([query])),
        ("rerank", lambda: reranker.rerank(query, [document])),
    ):
        started = time.perf_counter()
        try:
            value = action()
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            result["calls"].append(
                {
                    "operation": name,
                    "model": embedder.model_name if name == "embedding" else reranker.model_name,
                    "elapsed_ms": elapsed_ms,
                    "result_shape": len(value),
                    "status": "PASS",
                }
            )
        except Exception as exc:  # pragma: no cover - requires external service
            result["calls"].append(
                {
                    "operation": name,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    "status": "FAIL",
                    "error_type": type(exc).__name__,
                }
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "calls": result["calls"]}, ensure_ascii=False))
    return 0 if all(item["status"] == "PASS" for item in result["calls"]) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual, synthetic DashScope smoke test.")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts" / "external-smoke" / "result.json"
    )
    return run(parser.parse_args().output)


if __name__ == "__main__":
    raise SystemExit(main())
