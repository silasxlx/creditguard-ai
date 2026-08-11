from __future__ import annotations

from app.config import get_settings
from app.demo import SCENARIOS, scenario_materials
from app.main import app
from app.models import DocumentType
from app.parsing import parse_document


def test_demo_routes_are_hidden_by_default() -> None:
    assert get_settings().demo_mode is False
    assert "/api/v1/demo/scenarios/{scenario_id}" not in app.openapi()["paths"]


def test_demo_materials_cover_required_formats_and_scenarios() -> None:
    normal = scenario_materials("DEMO-NORMAL-001")
    high = scenario_materials("DEMO-HIGH-001")

    assert set(SCENARIOS) == {"DEMO-NORMAL-001", "DEMO-HIGH-001"}
    assert [item[0] for item in normal] == [
        DocumentType.BUSINESS_LICENSE,
        DocumentType.CREDIT_APPLICATION,
        DocumentType.DUE_DILIGENCE,
        DocumentType.FINANCIAL_STATEMENTS,
    ]
    assert [item[1] for item in normal] == [
        "business-license.pdf",
        "credit-application.docx",
        "due-diligence.pdf",
        "financial-statements.xlsx",
    ]
    assert all(content for _, _, _, content in normal + high)
    assert normal[2][3] != high[2][3]
    parsed = parse_document("demo-high-due", high[2][3], high[2][1])
    assert any("申请期限：48个月" in block.text for block in parsed.blocks)
