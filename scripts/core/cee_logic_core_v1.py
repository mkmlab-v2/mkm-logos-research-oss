from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge


@dataclass(frozen=True)
class CEEInput:
    case_id: str
    raw_text: str
    compressed_text: str
    reconstructed_text: str
    corpus_type: str = "canonical"
    metadata: dict[str, Any] | None = None


def _lambda_sep_025(vector_4d: dict[str, float]) -> float:
    target = 0.25
    return (
        abs(float(vector_4d.get("S", target)) - target)
        + abs(float(vector_4d.get("L", target)) - target)
        + abs(float(vector_4d.get("K", target)) - target)
        + abs(float(vector_4d.get("M", target)) - target)
    ) / 4.0


def _post_it(corpus_type: str, lambda_deviation: float) -> dict[str, str]:
    lane = "A-track" if corpus_type == "canonical" else "B-track"
    if lambda_deviation <= 0.01:
        balance = "near_sep_0_25"
    elif lambda_deviation <= 0.03:
        balance = "moderate_deviation"
    else:
        balance = "high_deviation"
    return {
        "lane": lane,
        "balance_band": balance,
        "note": "numeric-bias-reduced (not hallucination-free)",
    }


def run_cee_logic_core_v1(payload: CEEInput) -> dict[str, Any]:
    gematria = build_gematria_metadata(
        raw_text=payload.raw_text,
        compressed_text=payload.compressed_text,
        reconstructed_text=payload.reconstructed_text,
    )
    bridge = build_gematria_4d_bridge(gematria_metadata=gematria)
    vector_4d = dict(bridge.get("vector_4d") or {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25})
    vec_sum = float(vector_4d["S"]) + float(vector_4d["L"]) + float(vector_4d["K"]) + float(vector_4d["M"])
    lambda_dev = _lambda_sep_025(vector_4d)
    return {
        "schema": "cee_logic_core_v1",
        "case_id": payload.case_id,
        "corpus_type": payload.corpus_type,
        "gematria_metadata": gematria,
        "vector_4d": vector_4d,
        "vector_sum": vec_sum,
        "sep_target": 0.25,
        "lambda_deviation": lambda_dev,
        "state_id": bridge.get("state16"),
        "distance_to_state16": bridge.get("distance_to_state16"),
        "metadata_post_it": _post_it(payload.corpus_type, lambda_dev),
        "metadata": payload.metadata or {},
    }
