from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".ps1",
    ".toml",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".ts",
    ".tsx",
    ".vue",
    ".css",
    ".html",
}
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "artifacts",
    "data",
    "uploads",
    "logs",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
EXCLUDED_FILES = {".env.example", "uv.lock", "package-lock.json", "security_scan.py"}
SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?"
        r"(?!\$\{?)(?!<)(?!none\b)(?!null\b)[A-Za-z0-9+/=_-]{16,}"
    ),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
)
ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?i)(?:[A-Z]:\\|/Users/|/home/|/root/)"
)
FORBIDDEN_RULE_PATTERN = re.compile(r"(?i)\b(?:eval|exec|shell|subprocess|os\.system)\b")


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in EXCLUDED_PARTS for part in path.parts) or path.name in EXCLUDED_FILES:
            continue
        yield path


def scan(root: Path = ROOT) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in _iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append({"type": "NON_UTF8_TEXT", "path": str(path.relative_to(root))})
            continue
        relative = str(path.relative_to(root))
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append({"type": "POSSIBLE_SECRET", "path": relative})
                break
        if ABSOLUTE_PATH_PATTERN.search(text):
            findings.append({"type": "ABSOLUTE_LOCAL_PATH", "path": relative})
        if relative.replace("\\", "/") == "config/rules/rule-pack-v1.yaml" and FORBIDDEN_RULE_PATTERN.search(text):
            findings.append({"type": "DYNAMIC_RULE_OPERATOR", "path": relative})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository text for secrets and unsafe PoC artefacts.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    findings = scan(args.root)
    payload = {"findings": findings, "status": "PASS" if not findings else "FAIL"}
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif findings:
        for finding in findings:
            print(f"{finding['type']}: {finding['path']}")
    else:
        print("security scan passed")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
