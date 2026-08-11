from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "README.md",
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "demo-guide.md",
    ROOT / "docs" / "evaluation.md",
    ROOT / "docs" / "acceptance" / "poc-v0.1.0.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "CODE_OF_CONDUCT.md",
    ROOT / "CHANGELOG.md",
    ROOT / "docs" / "assets" / "dashboard.png",
    ROOT / "docs" / "assets" / "fact-review.png",
    ROOT / "docs" / "assets" / "rule-results.png",
    ROOT / "docs" / "assets" / "report-review.png",
    ROOT / "docs" / "assets" / "demo.gif",
]
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FORBIDDEN = re.compile(r"(?:[A-Za-z]:\\|-----BEGIN .*PRIVATE KEY-----|sk-[A-Za-z0-9]{16,})")


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED:
        if not path.exists():
            errors.append(f"missing release file: {path.relative_to(ROOT)}")
    gif = ROOT / "docs" / "assets" / "demo.gif"
    if gif.exists() and gif.stat().st_size > 8 * 1024 * 1024:
        errors.append("demo.gif exceeds the 8MB release limit")

    for markdown in [path for path in REQUIRED if path.suffix == ".md"]:
        text = markdown.read_text(encoding="utf-8")
        if FORBIDDEN.search(text):
            errors.append(f"sensitive-looking content in {markdown.relative_to(ROOT)}")
        for link in LINK_PATTERN.findall(text):
            if link.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = (markdown.parent / link.split("#", 1)[0]).resolve()
            if not target.exists():
                errors.append(f"broken link in {markdown.relative_to(ROOT)}: {link}")
    print("release docs: PASS" if not errors else "release docs: FAIL")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
