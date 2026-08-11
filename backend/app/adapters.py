from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field


class ParsedBlock(BaseModel):
    document_version_id: str = ""
    block_id: str
    evidence_id: str | None = None
    page: int | None = None
    block_type: str = "text"
    text: str
    source: str
    locator: dict[str, object] = Field(default_factory=dict)
    section_path: list[str] = Field(default_factory=list)
    reading_order: int = 0
    provider: str = "local"


class FactCandidate(BaseModel):
    field: str
    normalized_value: str | int | float | None
    evidence_id: str | None = None


class DocumentParser(Protocol):
    def parse(
        self, document_version_id: str, content: bytes, filename: str
    ) -> list[ParsedBlock]: ...


class FactExtractor(Protocol):
    def extract(self, blocks: list[ParsedBlock]) -> list[FactCandidate]: ...


class ReadOnlyTool(Protocol):
    name: str

    def call(self, customer_key: str) -> dict[str, object]: ...


class MockDocumentParser:
    def parse(self, document_version_id: str, content: bytes, filename: str) -> list[ParsedBlock]:
        text = content.decode("utf-8", errors="ignore").strip() or "mock parsed content"
        return [
            ParsedBlock(
                block_id=f"mock-{document_version_id}-1",
                page=1,
                text=text[:600],
                source=filename,
                locator={"page": 1, "reading_order": 0},
            )
        ]


class MockFactExtractor:
    def extract(self, blocks: list[ParsedBlock]) -> list[FactCandidate]:
        if not blocks:
            return []
        return [
            FactCandidate(
                field="mock_field", normalized_value="mock", evidence_id=blocks[0].block_id
            )
        ]


@dataclass(frozen=True)
class MockReadOnlyTool:
    name: str
    response: dict[str, object]

    def call(self, customer_key: str) -> dict[str, object]:
        return {**self.response, "customer_key": customer_key, "source": "mock"}


class ToolRegistry:
    def __init__(self, tools: list[MockReadOnlyTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def call(self, name: str, customer_key: str) -> dict[str, object]:
        if name not in self._tools:
            raise ValueError(f"Tool is not allowlisted: {name}")
        return self._tools[name].call(customer_key)
