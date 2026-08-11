from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

import yaml

from .models import DocumentStatus, DocumentType

RuleStatus = Literal["PASS", "WARN", "FAIL", "NEEDS_REVIEW"]
SUMMARY_PRIORITY = {"PASS": 0, "WARNING": 1, "NON_COMPLIANT": 2, "REVIEW_BLOCKED": 3}


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    name: str
    predicate: str
    query_template: str


@dataclass(frozen=True)
class RulePack:
    version: str
    name: str
    sha256: str
    allowed_operators: frozenset[str]
    rules: tuple[RuleDefinition, ...]


@dataclass(frozen=True)
class RuleEvaluationContext:
    facts: dict[str, Any]
    documents: list[dict[str, Any]]
    review_date: date
    tools: dict[str, dict[str, Any]]
    retrieval: dict[str, list[dict[str, Any]]]
    conflict_ids: list[str]


def load_rule_pack(path: Path) -> RulePack:
    content = path.read_bytes()
    payload = yaml.safe_load(content.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Rule pack must be a YAML object")
    allowed_operators = frozenset(str(item) for item in payload.get("allowed_operators", []))
    required_operators = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "is_present"}
    if not required_operators.issubset(allowed_operators):
        raise ValueError("Rule pack is missing a required allowlisted operator")
    definitions: list[RuleDefinition] = []
    for item in payload.get("rules", []):
        if not isinstance(item, dict):
            raise ValueError("Each rule must be an object")
        predicate = str(item.get("predicate", ""))
        if predicate not in {
            "required_materials",
            "company_age",
            "industry_admission",
            "blacklist_clear",
            "customer_risk",
            "loan_purpose",
            "tenor_limit",
            "available_exposure",
            "leverage_ratio",
            "current_ratio",
        }:
            raise ValueError(f"Unknown rule predicate: {predicate}")
        definitions.append(
            RuleDefinition(
                rule_id=str(item["id"]),
                name=str(item["name"]),
                predicate=predicate,
                query_template=str(item["query_template"]),
            )
        )
    if [definition.rule_id for definition in definitions] != [f"R{i:02d}" for i in range(1, 11)]:
        raise ValueError("Credit review rule pack must contain R01 through R10 in order")
    return RulePack(
        version=str(payload["version"]),
        name=str(payload["name"]),
        sha256=hashlib.sha256(content).hexdigest(),
        allowed_operators=allowed_operators,
        rules=tuple(definitions),
    )


def _fact_value(facts: dict[str, Any], field: str) -> Any:
    item = facts.get("fields", {}).get(field, {})
    return item.get("selected_value")


def _fact_evidence(facts: dict[str, Any], field: str) -> list[str]:
    item = facts.get("fields", {}).get(field, {})
    selected = [candidate for candidate in item.get("candidates", []) if candidate.get("selected")]
    candidates = selected or item.get("candidates", [])[:1]
    return [
        str(candidate.get("evidence_id"))
        for candidate in candidates
        if candidate.get("evidence_id")
    ]


def _result(
    definition: RuleDefinition,
    status: RuleStatus,
    message: str,
    evidence_refs: list[str],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "rule_id": definition.rule_id,
        "rule_name": definition.name,
        "status": status,
        "message": message,
        "details": details or {},
        "evidence_refs": sorted(set(evidence_refs)),
    }


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _anniversary(established: date, review_year: int) -> date:
    try:
        return established.replace(year=review_year)
    except ValueError:
        return established.replace(year=review_year, month=2, day=28)


def _tool(tools: dict[str, dict[str, Any]], name: str) -> dict[str, Any] | None:
    value = tools.get(name)
    if not value or value.get("status") != "OK":
        return None
    return value.get("data") if isinstance(value.get("data"), dict) else None


def evaluate_rule(definition: RuleDefinition, context: RuleEvaluationContext) -> dict[str, Any]:
    facts = context.facts
    retrieval_refs = [
        str(hit.get("chunk_id"))
        for hit in context.retrieval.get(definition.rule_id, [])
        if hit.get("selected") and hit.get("chunk_id")
    ]
    if not retrieval_refs and definition.predicate in {
        "industry_admission",
        "loan_purpose",
        "tenor_limit",
    }:
        return _result(definition, "NEEDS_REVIEW", "制度证据不可用。", retrieval_refs)

    if definition.predicate == "required_materials":
        required = set(DocumentType)
        present = {
            str(item.get("document_type"))
            for item in context.documents
            if item.get("status") == DocumentStatus.PARSED.value
        }
        missing = sorted(item.value for item in required if item.value not in present)
        rejected = [
            str(item.get("document_type"))
            for item in context.documents
            if item.get("status") == DocumentStatus.REJECTED.value
        ]
        if rejected:
            return _result(definition, "FAIL", "必需材料被拒绝。", rejected, {"rejected": rejected})
        if missing:
            supplied_types = {str(item.get("document_type")) for item in context.documents}
            status: RuleStatus = (
                "FAIL"
                if any(item.value not in supplied_types for item in required)
                else "NEEDS_REVIEW"
            )
            return _result(
                definition, status, "必需材料缺失或解析不可用。", missing, {"missing": missing}
            )
        return _result(
            definition,
            "PASS",
            "四类必需材料均已解析。",
            [str(item.get("id")) for item in context.documents],
        )

    if definition.predicate == "company_age":
        value = _fact_value(facts, "F03")
        evidence = _fact_evidence(facts, "F03")
        try:
            established = date.fromisoformat(str(value))
        except ValueError:
            return _result(definition, "NEEDS_REVIEW", "成立日期缺失或无效。", evidence)
        if established > context.review_date:
            return _result(definition, "NEEDS_REVIEW", "成立日期晚于审查日期。", evidence)
        return _result(
            definition,
            "PASS"
            if context.review_date >= _anniversary(established, context.review_date.year)
            else "FAIL",
            "企业成立年限满足要求。"
            if context.review_date >= _anniversary(established, context.review_date.year)
            else "企业成立年限不足一年。",
            evidence,
            {
                "establishment_date": established.isoformat(),
                "review_date": context.review_date.isoformat(),
            },
        )

    if definition.predicate == "industry_admission":
        value = str(_fact_value(facts, "F05") or "")
        evidence = _fact_evidence(facts, "F05") + retrieval_refs
        allowed = {"制造业", "信息技术", "批发零售业"}
        restricted = {"医药", "建筑业"}
        prohibited = {"房地产开发", "博彩", "钢铁产能过剩行业"}
        if value in allowed:
            status, message = "PASS", "行业属于允许准入范围。"
        elif value in restricted:
            status, message = "WARN", "行业属于受限行业。"
        elif value in prohibited:
            status, message = "FAIL", "行业属于禁止准入范围。"
        else:
            status, message = "NEEDS_REVIEW", "行业无法映射到制度分类。"
        return _result(definition, status, message, evidence, {"industry": value})

    if definition.predicate == "blacklist_clear":
        result = _tool(context.tools, "check_blacklist")
        if result is None or not isinstance(result.get("matched"), bool):
            return _result(
                definition, "NEEDS_REVIEW", "黑名单工具结果不可用。", ["tool:check_blacklist"]
            )
        return _result(
            definition,
            "FAIL" if result["matched"] else "PASS",
            "命中黑名单。" if result["matched"] else "未命中黑名单。",
            ["tool:check_blacklist"],
            result,
        )

    if definition.predicate == "customer_risk":
        result = _tool(context.tools, "get_customer_profile")
        status_value = result.get("risk_status") if result else None
        mapping: dict[str, tuple[RuleStatus, str]] = {
            "NORMAL": ("PASS", "客户风险状态正常。"),
            "WATCH": ("WARN", "客户风险状态为关注。"),
            "HIGH_RISK": ("FAIL", "客户风险状态为高风险。"),
        }
        if status_value not in mapping:
            return _result(
                definition,
                "NEEDS_REVIEW",
                "客户风险工具结果不可用。",
                ["tool:get_customer_profile"],
            )
        status, message = mapping[status_value]
        return _result(definition, status, message, ["tool:get_customer_profile"], result)

    if definition.predicate == "loan_purpose":
        value = str(_fact_value(facts, "F09") or "")
        evidence = _fact_evidence(facts, "F09") + retrieval_refs
        allowed = {"流动资金", "采购原材料", "支付工资", "日常经营周转", "置换短期经营性负债"}
        prohibited = {"房地产投机", "股票证券投资", "期货投资", "赌博"}
        if value in allowed:
            status, message = "PASS", "贷款用途属于允许范围。"
        elif value in prohibited:
            status, message = "FAIL", "贷款用途属于禁止范围。"
        else:
            status, message = "NEEDS_REVIEW", "贷款用途无法归一到制度分类。"
        return _result(definition, status, message, evidence, {"purpose": value})

    if definition.predicate == "tenor_limit":
        value = _fact_value(facts, "F08")
        evidence = _fact_evidence(facts, "F08") + retrieval_refs
        if not isinstance(value, int) or value <= 0:
            return _result(definition, "NEEDS_REVIEW", "贷款期限缺失、非整数或不大于零。", evidence)
        status: RuleStatus = "PASS" if value <= 36 else "FAIL"
        return _result(
            definition,
            status,
            "期限满足36个月上限。" if status == "PASS" else "期限超过36个月上限。",
            evidence,
            {"months": value},
        )

    if definition.predicate == "available_exposure":
        requested = _decimal(_fact_value(facts, "F06"))
        evidence = _fact_evidence(facts, "F06")
        exposure = _tool(context.tools, "get_credit_exposure")
        if requested is None or requested < 0 or exposure is None:
            return _result(
                definition,
                "NEEDS_REVIEW",
                "额度或工具结果不可用。",
                evidence + ["tool:get_credit_exposure"],
            )
        available = _decimal(exposure.get("available_amount"))
        if (
            available is None
            or available < 0
            or str(_fact_value(facts, "F07")) != str(exposure.get("currency"))
        ):
            return _result(
                definition,
                "NEEDS_REVIEW",
                "额度缺失、为负或币种不一致。",
                evidence + ["tool:get_credit_exposure"],
            )
        status = "PASS" if requested <= available else "FAIL"
        return _result(
            definition,
            status,
            "申请金额不超过可用额度。" if status == "PASS" else "申请金额超过可用额度。",
            evidence + ["tool:get_credit_exposure"],
            {
                "requested_amount": str(requested),
                "available_amount": str(available),
                "currency": exposure.get("currency"),
            },
        )

    if definition.predicate == "leverage_ratio":
        assets = _decimal(_fact_value(facts, "F10"))
        liabilities = _decimal(_fact_value(facts, "F11"))
        evidence = _fact_evidence(facts, "F10") + _fact_evidence(facts, "F11") + retrieval_refs
        if assets is None or liabilities is None or assets <= 0 or liabilities < 0:
            return _result(definition, "NEEDS_REVIEW", "资产负债率计算输入不可用。", evidence)
        ratio = liabilities / assets * Decimal(100)
        status = "PASS" if ratio <= Decimal(70) else "FAIL"
        return _result(
            definition,
            status,
            "资产负债率满足70%边界。" if status == "PASS" else "资产负债率超过70%边界。",
            evidence,
            {"ratio_percent": str(ratio)},
        )

    if definition.predicate == "current_ratio":
        current_assets = _decimal(_fact_value(facts, "F12"))
        current_liabilities = _decimal(_fact_value(facts, "F13"))
        evidence = _fact_evidence(facts, "F12") + _fact_evidence(facts, "F13") + retrieval_refs
        if (
            current_assets is None
            or current_liabilities is None
            or current_assets < 0
            or current_liabilities <= 0
        ):
            return _result(definition, "NEEDS_REVIEW", "流动比率计算输入不可用。", evidence)
        ratio = current_assets / current_liabilities
        status = "PASS" if ratio >= Decimal("1.0") else "FAIL"
        return _result(
            definition,
            status,
            "流动比率满足1.0边界。" if status == "PASS" else "流动比率低于1.0边界。",
            evidence,
            {"ratio": str(ratio)},
        )

    return _result(definition, "NEEDS_REVIEW", "规则未实现。", [])


class RuleEngine:
    def __init__(self, rule_pack: RulePack) -> None:
        self.rule_pack = rule_pack

    def evaluate(self, context: RuleEvaluationContext) -> list[dict[str, Any]]:
        return [evaluate_rule(definition, context) for definition in self.rule_pack.rules]

    @staticmethod
    def summarize(results: list[dict[str, Any]]) -> str:
        statuses = {str(result["status"]) for result in results}
        if "NEEDS_REVIEW" in statuses:
            return "REVIEW_BLOCKED"
        if "FAIL" in statuses:
            return "NON_COMPLIANT"
        if "WARN" in statuses:
            return "WARNING"
        return "PASS"


__all__ = [
    "RuleDefinition",
    "RuleEngine",
    "RuleEvaluationContext",
    "RulePack",
    "RuleStatus",
    "load_rule_pack",
]
