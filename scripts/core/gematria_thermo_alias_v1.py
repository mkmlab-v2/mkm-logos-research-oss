"""Derived thermo notation (Ei, Pf, Dd, Hc) — NOT SSOT; parallel to S,L,K,M.

Recipe: gematria_thermo_alias_v1 (research report / legacy_thermo_alias fill only).
"""

from __future__ import annotations

import math
from typing import Any

from scripts.core.gematria_engine import build_gematria_metadata


def _digit_root(n: int) -> int:
    n = abs(int(n))
    if n == 0:
        return 9
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n if n > 0 else 9


def compute_thermo_alias(
    *,
    raw_text: str,
    compressed_text: str | None = None,
    reconstructed_text: str | None = None,
) -> dict[str, float]:
    """Compute Ei/Pf/Dd/Hc from gematria inputs (derived layer only)."""
    compressed = compressed_text or raw_text
    reconstructed = reconstructed_text or compressed
    meta = build_gematria_metadata(
        raw_text=raw_text,
        compressed_text=compressed,
        reconstructed_text=reconstructed,
    )
    ei = float(meta.get("raw_combined_sum", 0))
    pf = float(_digit_root(int(ei)) % 9 or 9)
    char_count = max(1, len("".join(ch for ch in compressed if not ch.isspace())))
    script_chars = max(1, int(meta.get("raw_greek_sum", 0) > 0) + int(meta.get("raw_hebrew_sum", 0) > 0))
    dd = round((ei / max(char_count, 1)) / math.sqrt(script_chars), 4)
    hc = round(math.cos(math.pi * (int(ei) % 26) / 26.0), 4)
    return {
        "energy_intensity_raw": ei,
        "pulse_frequency_hz": pf,
        "density_coefficient": dd,
        "harmony_constant": hc,
    }


def thermo_alias_from_spec(spec: dict[str, Any]) -> dict[str, float]:
    texts = spec.get("gematria_texts")
    if isinstance(texts, dict):
        raw = str(texts.get("raw") or spec.get("gematria_text", ""))
        compressed = str(texts.get("compressed") or spec.get("gematria_text", raw))
        reconstructed = str(texts.get("reconstructed") or compressed)
    else:
        raw = compressed = reconstructed = str(spec.get("gematria_text", ""))
    return compute_thermo_alias(
        raw_text=raw,
        compressed_text=compressed,
        reconstructed_text=reconstructed,
    )
