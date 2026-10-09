"""Vendor-neutral contract. No network provider is configured in this release."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EvidencePassage:
    source_version_id: str
    locator: str
    text: str
    evidence_status: str


@dataclass(frozen=True)
class ModelRequest:
    task: str
    passages: tuple[EvidencePassage, ...]
    output_schema: dict
    maximum_cost: float = 0


class ModelProvider(Protocol):
    def propose(self, request: ModelRequest) -> dict:
        """Return a proposal, never execute a tool or promote company facts."""
        ...


class DisabledProvider:
    def propose(self, request: ModelRequest) -> dict:
        raise RuntimeError('No model provider configured. Local evidence/workflow tools remain available.')
