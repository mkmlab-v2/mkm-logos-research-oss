# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.7, K:0.5, M:0.5}
# Balance: 88
# Purpose: Optional 16-state side-channel adapter for compression eval rows (Phase A noop).
# Keywords: state16, compression, noop, adapter
"""Runtime insertion contract for 16-state mapping (Phase A: noop, non-blocking).

See docs/final/STATE16_INTERFACE_INSERTION_CONTRACT_2026-03-31.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


STATE16_NOT_ENABLED = "STATE16_NOT_ENABLED"
STATE16_INPUT_INVALID = "STATE16_INPUT_INVALID"
STATE16_PROVIDER_ERROR = "STATE16_PROVIDER_ERROR"
STATE16_OUT_OF_RANGE = "STATE16_OUT_OF_RANGE"


@dataclass
class State16Input:
    case_id: str
    raw_text: str
    compressed_text: str
    reconstructed_text: str
    route_domain: str | None
    route_shard_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class State16Output:
    state_id: int | None
    confidence: float | None
    error_code: str
    error_message: str

    def to_row_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "confidence": self.confidence,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


class State16Adapter(Protocol):
    def apply(self, inp: State16Input) -> State16Output:
        ...


def validate_state16_output(out: State16Output) -> None:
    """Raise ValueError if state_id / confidence are outside the contract range."""
    if out.state_id is not None and not (1 <= out.state_id <= 16):
        raise ValueError(f"state_id must be 1..16 or None, got {out.state_id!r}")
    if out.confidence is not None and not (0.0 <= out.confidence <= 1.0):
        raise ValueError(f"confidence must be 0..1 or None, got {out.confidence!r}")


class NoopState16Adapter:
    """Default adapter: feature off; records STATE16_NOT_ENABLED per case."""

    def apply(self, inp: State16Input) -> State16Output:
        _ = inp  # reserved for future real mappers
        return State16Output(
            state_id=None,
            confidence=None,
            error_code=STATE16_NOT_ENABLED,
            error_message="16-state runtime adapter disabled (Phase A noop).",
        )

    def map_state(self, inp: State16Input) -> State16Output:
        return self.apply(inp)
