from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from .adapters import ParsedBlock
from .parsing import ParsedDocument

FACT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "F01": {"name": "企业名称", "type": "string", "aliases": ["企业名称", "公司名称", "客户名称"]},
    "F02": {
        "name": "统一社会信用代码",
        "type": "string",
        "aliases": ["统一社会信用代码", "社会信用代码"],
    },
    "F03": {"name": "成立日期", "type": "date", "aliases": ["成立日期", "成立时间"]},
    "F04": {"name": "法定代表人", "type": "string", "aliases": ["法定代表人", "法人代表"]},
    "F05": {"name": "所属行业", "type": "enum", "aliases": ["所属行业", "行业"]},
    "F06": {"name": "申请金额", "type": "decimal", "aliases": ["申请金额", "授信金额", "贷款金额"]},
    "F07": {"name": "币种", "type": "currency", "aliases": ["币种", "货币"]},
    "F08": {"name": "申请期限", "type": "integer", "aliases": ["申请期限", "贷款期限", "期限"]},
    "F09": {"name": "贷款用途", "type": "enum", "aliases": ["贷款用途", "借款用途", "用途"]},
    "F10": {"name": "总资产", "type": "decimal", "aliases": ["总资产", "资产总额"]},
    "F11": {"name": "总负债", "type": "decimal", "aliases": ["总负债", "负债总额"]},
    "F12": {"name": "流动资产", "type": "decimal", "aliases": ["流动资产"]},
    "F13": {"name": "流动负债", "type": "decimal", "aliases": ["流动负债"]},
    "F14": {"name": "营业收入", "type": "decimal", "aliases": ["营业收入", "销售收入"]},
    "F15": {"name": "净利润", "type": "decimal", "aliases": ["净利润", "净利"]},
}


@dataclass
class FactCandidate:
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FactConflict:
    conflict_id: str
    field: str
    field_name: str
    comparison: str
    candidates: list[dict[str, Any]]
    difference: dict[str, str] | None
    material: bool
    selected_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strip_raw(value: str) -> str:
    return value.strip().strip("\"'“”‘’")


def normalize_value(field: str, raw_value: str) -> tuple[Any, list[str]]:
    definition = FACT_DEFINITIONS[field]
    value_type = definition["type"]
    raw = _strip_raw(raw_value)
    reasons: list[str] = []
    if not raw:
        return None, ["EMPTY"]
    if value_type == "string":
        return re.sub(r"\s+", "", raw) if field == "F02" else raw, reasons
    if value_type == "currency":
        currencies = {
            "人民币": "CNY",
            "元": "CNY",
            "CNY": "CNY",
            "RMB": "CNY",
            "美元": "USD",
            "USD": "USD",
        }
        normalized = currencies.get(raw.upper(), currencies.get(raw))
        if not normalized:
            reasons.append("UNKNOWN_CURRENCY")
        return normalized or raw.upper(), reasons
    if value_type == "date":
        match = re.search(r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})", raw)
        if not match:
            return None, ["INVALID_DATE"]
        try:
            return date(
                int(match.group(1)), int(match.group(2)), int(match.group(3))
            ).isoformat(), reasons
        except ValueError:
            return None, ["INVALID_DATE"]
    if value_type == "integer":
        match = re.search(r"-?\d+(?:\.\d+)?", raw)
        if not match:
            return None, ["INVALID_INTEGER"]
        try:
            number = Decimal(match.group(0))
            if "年" in raw and "个月" not in raw and "月" not in raw:
                number *= 12
            if number != number.to_integral_value():
                return None, ["NON_INTEGER"]
            return int(number), reasons
        except InvalidOperation:
            return None, ["INVALID_INTEGER"]
    if value_type == "decimal":
        multiplier = Decimal(1)
        if "亿元" in raw:
            multiplier = Decimal(100000000)
        elif "万元" in raw:
            multiplier = Decimal(10000)
        number_text = re.sub(r"[^0-9.+-]", "", raw)
        try:
            normalized = (Decimal(number_text) * multiplier).normalize()
            return format(normalized, "f"), reasons
        except (InvalidOperation, ValueError):
            return None, ["INVALID_DECIMAL"]
    return raw, reasons


def _candidate_from_block(field: str, block: ParsedBlock, raw: str) -> FactCandidate:
    definition = FACT_DEFINITIONS[field]
    normalized, reasons = normalize_value(field, raw)
    return FactCandidate(
        field=field,
        field_name=definition["name"],
        value_type=definition["type"],
        raw_value=raw,
        normalized_value=normalized,
        document_version_id=block.document_version_id,
        evidence_id=block.evidence_id or block.block_id,
        locator=block.locator,
        source=block.source,
        validation_reasons=reasons,
    )


def extract_candidates(parsed_documents: list[ParsedDocument]) -> list[FactCandidate]:
    candidates: list[FactCandidate] = []
    aliases: list[tuple[str, str]] = []
    for field, definition in FACT_DEFINITIONS.items():
        aliases.extend((field, alias) for alias in definition["aliases"])
    aliases.sort(key=lambda item: len(item[1]), reverse=True)
    for parsed in parsed_documents:
        for block in parsed.blocks:
            for field, alias in aliases:
                pattern = rf"(?:^|[\n|])\s*{re.escape(alias)}\s*[:：=]\s*([^\n|,，;；]+)"
                for match in re.finditer(pattern, block.text, flags=re.IGNORECASE):
                    candidates.append(_candidate_from_block(field, block, match.group(1)))
    # Same value from the same evidence is not a conflict and need not be duplicated.
    unique: dict[tuple[str, str, str, str], FactCandidate] = {}
    for candidate in candidates:
        key = (
            candidate.field,
            str(candidate.normalized_value),
            candidate.document_version_id,
            candidate.evidence_id,
        )
        unique.setdefault(key, candidate)
    return list(unique.values())


def _numeric_difference(left: Decimal, right: Decimal) -> dict[str, str]:
    absolute = abs(left - right)
    if left == 0 and right == 0:
        relative = Decimal(0)
    else:
        relative = absolute / max(abs(left), abs(right))
    return {"absolute": str(absolute), "relative": str(relative)}


def detect_conflicts(candidates: list[FactCandidate]) -> list[FactConflict]:
    by_field: dict[str, list[FactCandidate]] = {}
    for candidate in candidates:
        by_field.setdefault(candidate.field, []).append(candidate)
    conflicts: list[FactConflict] = []
    for field, values in by_field.items():
        distinct = {}
        for candidate in values:
            if candidate.normalized_value is not None:
                distinct.setdefault(str(candidate.normalized_value), candidate)
        if len(distinct) < 2:
            continue
        field_type = FACT_DEFINITIONS[field]["type"]
        comparison = "DISCRETE_EXACT"
        difference: dict[str, str] | None = None
        material = True
        if field_type == "decimal":
            comparison = "NUMERIC_ABSOLUTE_AND_RELATIVE"
            numbers = [Decimal(candidate.normalized_value) for candidate in distinct.values()]
            difference = _numeric_difference(numbers[0], numbers[1])
            material = Decimal(difference["absolute"]) > Decimal(10000) and Decimal(
                difference["relative"]
            ) > Decimal("0.01")
        conflict_seed = f"{field}|{'|'.join(sorted(distinct))}"
        conflict_id = hashlib.sha256(conflict_seed.encode("utf-8")).hexdigest()
        conflicts.append(
            FactConflict(
                conflict_id=conflict_id,
                field=field,
                field_name=FACT_DEFINITIONS[field]["name"],
                comparison=comparison,
                candidates=[candidate.to_dict() for candidate in distinct.values()],
                difference=difference,
                material=material,
            )
        )
    return conflicts


def build_fact_payload(parsed_documents: list[ParsedDocument]) -> dict[str, Any]:
    candidates = extract_candidates(parsed_documents)
    conflicts = detect_conflicts(candidates)
    fields: dict[str, dict[str, Any]] = {}
    for field, definition in FACT_DEFINITIONS.items():
        field_candidates = [
            candidate.to_dict() for candidate in candidates if candidate.field == field
        ]
        distinct_values = {str(item["normalized_value"]) for item in field_candidates}
        fields[field] = {
            "field": field,
            "field_name": definition["name"],
            "value_type": definition["type"],
            "candidates": field_candidates,
            "selected_value": field_candidates[0]["normalized_value"]
            if field_candidates and len(distinct_values) == 1
            else None,
            "requires_review": not field_candidates,
        }
    return {
        "schema_version": "1.0",
        "fields": fields,
        "missing_fields": [field for field, value in fields.items() if value["requires_review"]],
        "conflicts": [conflict.to_dict() for conflict in conflicts],
        "requires_review": bool(
            conflicts or any(value["requires_review"] for value in fields.values())
        ),
    }
