"""Map gematria 4D (S,L,K,M) to design-kernel draft params — B-track / HYPO only.

Does NOT merge into sasang_design_primitive_kernel_v1.json.
Outputs normalized UI Decide drafts for cosmic anchor sidecar rows.
"""

from __future__ import annotations

from typing import Any, Mapping

from tools.myeongni.gematria_myeongri_math_v1 import cosine_similarity

NORMALIZE_FN = "normalize_gematria_to_kernel_v1"
NORMALIZE_VERSION = "1.0.0"

_PRIMITIVE_PROFILES: dict[str, dict[str, float]] = {
    "pathology": {"S": 0.35, "L": 0.25, "K": 0.20, "M": 0.20},
    "circulation": {"S": 0.25, "L": 0.35, "K": 0.25, "M": 0.15},
    "survival": {"S": 0.20, "L": 0.20, "K": 0.25, "M": 0.35},
    "harmony": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
    "valence": {"S": 0.25, "L": 0.25, "K": 0.35, "M": 0.15},
}

_PARAM_BY_PRIMITIVE: dict[str, str] = {
    "pathology": "intensity_budget",
    "circulation": "motion_exchange",
    "survival": "spacing_survival",
    "harmony": "layout_harmony",
    "valence": "valence_arousal",
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def kernel_drafts_from_4d(vector_4d: Mapping[str, float]) -> dict[str, Any]:
    """Deterministic draft params from simplex 4D vector."""
    s = float(vector_4d.get("S", 0.25))
    l = float(vector_4d.get("L", 0.25))
    k = float(vector_4d.get("K", 0.25))
    m = float(vector_4d.get("M", 0.25))

    intensity = _clamp(0.35 + (s - 0.25) * 1.6 + (k - 0.25) * 0.4, 0.2, 0.9)
    pulse_ms = int(_clamp(4800 - l * 2400, 2400, 4800))
    transition_ms = int(_clamp(180 + (1.0 - l) * 140, 180, 320))
    min_padding = int(_clamp(12 + m * 24, 12, 36))
    max_blocks = int(_clamp(5 - m * 2, 2, 4))
    layout_density = _clamp(0.42 + (k - 0.25) * 0.5, 0.35, 0.58)
    contrast_cap = _clamp(0.40 - (s - 0.25) * 0.35, 0.22, 0.40)
    hue_bias = _clamp((k - m) * 0.7, -0.35, 0.35)

    return {
        "pathology": {
            "intensity_budget": round(intensity, 4),
            "state_band": (
                "calm"
                if intensity >= 0.65
                else "watch"
                if intensity >= 0.45
                else "stress"
            ),
        },
        "circulation": {
            "pulse_period_ms": pulse_ms,
            "transition_ms": transition_ms,
            "accent_budget_pct_max": int(_clamp(10 - m * 4, 6, 10)),
        },
        "survival": {
            "min_padding_px": min_padding,
            "max_blocks_per_view": max_blocks,
            "line_height_ratio": [round(1.45 + m * 0.12, 3), round(1.55 + m * 0.10, 3)],
        },
        "harmony": {
            "layout_density": round(layout_density, 4),
            "contrast_cap": round(contrast_cap, 4),
            "pair_kind": (
                "controlling"
                if s > 0.28 and m < 0.22
                else "generating"
                if m > 0.28
                else "same"
            ),
        },
        "valence": {"hue_warmth_bias": round(hue_bias, 4)},
    }


def rank_primitive_alignments(
    vector_4d: Mapping[str, float],
    *,
    top_n: int = 3,
) -> list[dict[str, Any]]:
    """Cosine similarity rows — resonance hypothesis, not dogma."""
    drafts = kernel_drafts_from_4d(vector_4d)
    scored: list[tuple[str, float]] = []
    for primitive, profile in _PRIMITIVE_PROFILES.items():
        sim = cosine_similarity(vector_4d, profile)
        scored.append((primitive, sim))
    scored.sort(key=lambda row: row[1], reverse=True)

    rows: list[dict[str, Any]] = []
    for primitive, sim in scored[:top_n]:
        param = _PARAM_BY_PRIMITIVE[primitive]
        rows.append(
            {
                "primitive": primitive,
                "param": param,
                "similarity": round(sim, 4),
                "draft": drafts[primitive],
                "alignment_note_ko": (
                    f"[HYPO] 4D cosine resonance row — {primitive}/{param}; "
                    "신학·체질 단정 아님"
                ),
            }
        )
    return rows


def _vector_spread_4d(vector_4d: Mapping[str, float]) -> float:
    vals = [float(vector_4d[k]) for k in ("S", "L", "K", "M")]
    return max(vals) - min(vals)


def rank_primitive_alignments_spread_aware(
    vector_4d: Mapping[str, float],
    *,
    thermo_alias: Mapping[str, float] | None = None,
    top_n: int = 3,
    spread_floor: float = 0.08,
) -> list[dict[str, Any]]:
    """B-track ranking: penalize harmony top-1 when 4D/thermo spread is too flat."""
    drafts = kernel_drafts_from_4d(vector_4d)
    spread_4d = _vector_spread_4d(vector_4d)
    thermo = thermo_alias or {}
    pf = float(thermo.get("pulse_frequency_hz", 5.0))
    dd = float(thermo.get("density_coefficient", 0.0))
    thermo_spread = abs(pf - 5.0) / 4.0 + min(abs(dd) / 500.0, 1.0)
    flat_penalty = max(0.0, spread_floor - spread_4d) * 3.0
    thermo_gate = thermo_spread < 0.12

    scored: list[tuple[str, float, float]] = []
    for primitive, profile in _PRIMITIVE_PROFILES.items():
        sim = cosine_similarity(vector_4d, profile)
        adj = sim
        if primitive == "harmony" and (flat_penalty > 0.0 or thermo_gate):
            adj -= flat_penalty + (0.05 if thermo_gate else 0.0)
        scored.append((primitive, sim, adj))
    scored.sort(key=lambda row: row[2], reverse=True)

    rows: list[dict[str, Any]] = []
    for primitive, sim, adj in scored[:top_n]:
        param = _PARAM_BY_PRIMITIVE[primitive]
        rows.append(
            {
                "primitive": primitive,
                "param": param,
                "similarity": round(sim, 4),
                "similarity_adjusted": round(adj, 4),
                "draft": drafts[primitive],
                "alignment_note_ko": (
                    f"[HYPO] spread-aware cosine row — {primitive}/{param}; "
                    "harmony penalty when flat; 신학·체질 단정 아님"
                ),
            }
        )
    return rows
