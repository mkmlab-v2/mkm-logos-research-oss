from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE16_PROBE = ROOT / "data" / "myeongni" / "16_STATE_MASTER_PROBE_v1.json"


@dataclass(frozen=True)
class StateVector:
    state_id: int
    vector_4d: dict[str, float]


def _load_state_vectors(probe_path: Path) -> list[StateVector]:
    doc = json.loads(probe_path.read_text(encoding="utf-8"))
    rows = []
    for entry in doc.get("states", []):
        sid = int(entry.get("state_id"))
        vec = entry.get("vector_4d") or {}
        rows.append(
            StateVector(
                state_id=sid,
                vector_4d={
                    "S": float(vec.get("S", 0.25)),
                    "L": float(vec.get("L", 0.25)),
                    "K": float(vec.get("K", 0.25)),
                    "M": float(vec.get("M", 0.25)),
                },
            )
        )
    return rows


def _normalize_to_4d(raw_sum: int, compressed_sum: int, reconstructed_sum: int) -> dict[str, float]:
    # Keep values around 0.25 baseline while preserving deterministic spread.
    d1 = ((raw_sum % 101) - 50) / 10000.0
    d2 = ((compressed_sum % 101) - 50) / 10000.0
    d3 = ((reconstructed_sum % 101) - 50) / 10000.0
    s = 0.25 + d1
    l = 0.25 + d2
    k = 0.25 + d3
    m = 1.0 - (s + l + k)
    return {"S": s, "L": l, "K": k, "M": m}


def _distance(a: dict[str, float], b: dict[str, float]) -> float:
    return (
        (a["S"] - b["S"]) ** 2
        + (a["L"] - b["L"]) ** 2
        + (a["K"] - b["K"]) ** 2
        + (a["M"] - b["M"]) ** 2
    ) ** 0.5


def build_gematria_4d_bridge(
    *,
    gematria_metadata: dict[str, int],
    probe_path: Path | None = None,
) -> dict[str, object]:
    path = probe_path or DEFAULT_STATE16_PROBE
    states = _load_state_vectors(path)
    vec = _normalize_to_4d(
        int(gematria_metadata.get("raw_combined_sum", 0)),
        int(gematria_metadata.get("compressed_combined_sum", 0)),
        int(gematria_metadata.get("reconstructed_combined_sum", 0)),
    )
    best = min(states, key=lambda row: _distance(vec, row.vector_4d)) if states else None
    if best is None:
        return {
            "vector_4d": vec,
            "state16": None,
            "distance_to_state16": None,
            "probe_path": str(path.as_posix()),
        }
    return {
        "vector_4d": vec,
        "state16": int(best.state_id),
        "distance_to_state16": _distance(vec, best.vector_4d),
        "probe_path": str(path.as_posix()),
    }
