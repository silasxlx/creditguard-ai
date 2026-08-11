from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_TEXT_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "NOTICE",
    "docs/architecture.md",
    "docs/demo-guide.md",
    "docs/evaluation.md",
    "evals/README.md",
    "pyproject.toml",
    "web/index.html",
    "web/src/App.vue",
)
FORBIDDEN_MARKERS = ("PoC", "poc-", "SPEC-003", "SPEC/")


def test_public_repository_excludes_internal_documents() -> None:
    for relative in (
        "AGENTS.md",
        "SPEC",
        "docs/acceptance/poc-v0.1.0.md",
        "fixtures/policies",
    ):
        assert not (ROOT / relative).exists(), relative


def test_public_surface_has_no_internal_or_legacy_branding() -> None:
    findings = []
    for relative in PUBLIC_TEXT_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                findings.append(f"{relative}: {marker}")
    assert findings == []
