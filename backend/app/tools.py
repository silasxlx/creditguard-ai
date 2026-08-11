from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["OK", "ERROR"]
    tool_name: str
    customer_key: str
    data: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CustomerProfileData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    industry_status: Literal["ALLOWED", "RESTRICTED", "PROHIBITED", "UNKNOWN"]
    risk_status: Literal["NORMAL", "WATCH", "HIGH_RISK", "UNKNOWN"]
    as_of: datetime
    source: str


class CreditExposureData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_amount: str
    used_amount: str
    available_amount: str
    currency: str
    as_of: datetime


class BlacklistData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched: bool
    list_type: str | None = None
    as_of: datetime
    source: str


@dataclass(frozen=True)
class ToolProfile:
    customer_key: str
    industry_status: str = "ALLOWED"
    risk_status: str = "NORMAL"
    approved_amount: str = "2000000"
    used_amount: str = "500000"
    available_amount: str = "1500000"
    currency: str = "CNY"
    blacklist_matched: bool = False
    failure_names: frozenset[str] = frozenset()


class ReadOnlyToolRegistry:
    """Allowlisted, deterministic, read-only tools for the reference implementation."""

    ALLOWED = frozenset({"get_customer_profile", "get_credit_exposure", "check_blacklist"})

    def __init__(self, profiles: dict[str, ToolProfile] | None = None) -> None:
        self.profiles = profiles or {}

    def _profile(self, customer_key: str) -> ToolProfile:
        return self.profiles.get(customer_key, ToolProfile(customer_key=customer_key))

    def call(self, name: str, customer_key: str, run_id: str) -> ToolEnvelope:
        if name not in self.ALLOWED:
            raise ValueError(f"Tool is not allowlisted: {name}")
        profile = self._profile(customer_key)
        if name in profile.failure_names:
            return ToolEnvelope(
                status="ERROR",
                tool_name=name,
                customer_key=customer_key,
                error_code="TOOL_UNAVAILABLE",
            )
        now = datetime.now(UTC)
        if name == "get_customer_profile":
            data = CustomerProfileData(
                industry_status=profile.industry_status,  # type: ignore[arg-type]
                risk_status=profile.risk_status,  # type: ignore[arg-type]
                as_of=now,
                source=f"synthetic-profile:{run_id}",
            )
        elif name == "get_credit_exposure":
            data = CreditExposureData(
                approved_amount=profile.approved_amount,
                used_amount=profile.used_amount,
                available_amount=profile.available_amount,
                currency=profile.currency,
                as_of=now,
            )
        else:
            data = BlacklistData(
                matched=profile.blacklist_matched,
                list_type="synthetic" if profile.blacklist_matched else None,
                as_of=now,
                source=f"synthetic-blacklist:{run_id}",
            )
        return ToolEnvelope(
            status="OK",
            tool_name=name,
            customer_key=customer_key,
            data=data.model_dump(mode="json"),
            as_of=now,
        )


def call_required_tools(
    registry: ReadOnlyToolRegistry, customer_key: str, run_id: str
) -> dict[str, dict[str, Any]]:
    return {
        name: registry.call(name, customer_key, run_id).model_dump(mode="json")
        for name in ("get_customer_profile", "get_credit_exposure", "check_blacklist")
    }


__all__ = [
    "BlacklistData",
    "CreditExposureData",
    "CustomerProfileData",
    "ReadOnlyToolRegistry",
    "ToolEnvelope",
    "ToolProfile",
    "call_required_tools",
]
