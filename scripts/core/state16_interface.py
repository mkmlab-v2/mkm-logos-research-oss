# @MKM12-METADATA
# Type: Interface
# Vector: {S:0.7, L:0.8, K:0.8, M:0.6}
# Balance: 90
# Purpose: Define insertion contract for optional 16-state normalization.
# Keywords: state16, contract, normalization, interface
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class State16Input:
    case_id: str
    raw_text: str
    compressed_text: str
    reconstructed_text: str
    route_domain: str | None
    route_shard_id: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class State16Output:
    state_id: int | None
    confidence: float | None
    error_code: str | None = None
    error_message: str | None = None


class State16Adapter(Protocol):
    def map_state(self, payload: State16Input) -> State16Output:
        """Return normalized state mapping (1..16) or explicit skip/error."""


class NoopState16Adapter:
    """Safe default until runtime cutover is approved."""

    def map_state(self, payload: State16Input) -> State16Output:
        _ = payload
        return State16Output(state_id=None, confidence=None, error_code="STATE16_NOT_ENABLED")


def validate_state16_output(output: State16Output) -> None:
    if output.state_id is None:
        return
    if not 1 <= output.state_id <= 16:
        raise ValueError("state_id must be within 1..16")
    if output.confidence is None or not (0.0 <= output.confidence <= 1.0):
        raise ValueError("confidence must be within 0..1 when state_id is present")
