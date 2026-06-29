"""scriptures-js gematria helpers — lookup layer only [HYPO].

Letter tables aligned with @metaxia/scriptures-core (MIT). Maps sums to S-L-K-M
via production gematria_bridge_v1 — no prophecy claims.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

KERNEL_RECIPE_ID = "gematria_bridge_v1"

HEBREW_HECHRACHI: dict[str, int] = {
    "א": 1,
    "ב": 2,
    "ג": 3,
    "ד": 4,
    "ה": 5,
    "ו": 6,
    "ז": 7,
    "ח": 8,
    "ט": 9,
    "י": 10,
    "כ": 20,
    "ל": 30,
    "מ": 40,
    "נ": 50,
    "ס": 60,
    "ע": 70,
    "פ": 80,
    "צ": 90,
    "ק": 100,
    "ר": 200,
    "ש": 300,
    "ת": 400,
    "ך": 20,
    "ם": 40,
    "ן": 50,
    "ף": 80,
    "ץ": 90,
}

HEBREW_KATAN: dict[str, int] = {
    "א": 1,
    "ב": 2,
    "ג": 3,
    "ד": 4,
    "ה": 5,
    "ו": 6,
    "ז": 7,
    "ח": 8,
    "ט": 9,
    "י": 1,
    "כ": 2,
    "ל": 3,
    "מ": 4,
    "נ": 5,
    "ס": 6,
    "ע": 7,
    "פ": 8,
    "צ": 9,
    "ק": 1,
    "ר": 2,
    "ש": 3,
    "ת": 4,
    "ך": 2,
    "ם": 4,
    "ן": 5,
    "ף": 8,
    "ץ": 9,
}

HEBREW_SIDURI: dict[str, int] = {
    "א": 1,
    "ב": 2,
    "ג": 3,
    "ד": 4,
    "ה": 5,
    "ו": 6,
    "ז": 7,
    "ח": 8,
    "ט": 9,
    "י": 10,
    "כ": 11,
    "ל": 12,
    "מ": 13,
    "נ": 14,
    "ס": 15,
    "ע": 16,
    "פ": 17,
    "צ": 18,
    "ק": 19,
    "ר": 20,
    "ש": 21,
    "ת": 22,
    "ך": 11,
    "ם": 13,
    "ן": 14,
    "ף": 17,
    "ץ": 18,
}

GREEK_STANDARD: dict[str, int] = {
    "Α": 1,
    "Β": 2,
    "Γ": 3,
    "Δ": 4,
    "Ε": 5,
    "Ϛ": 6,
    "Ζ": 7,
    "Η": 8,
    "Θ": 9,
    "Ι": 10,
    "Κ": 20,
    "Λ": 30,
    "Μ": 40,
    "Ν": 50,
    "Ξ": 60,
    "Ο": 70,
    "Π": 80,
    "Ϟ": 90,
    "Ρ": 100,
    "Σ": 200,
    "Τ": 300,
    "Υ": 400,
    "Φ": 500,
    "Χ": 600,
    "Ψ": 700,
    "Ω": 800,
    "Ϡ": 900,
    "α": 1,
    "β": 2,
    "γ": 3,
    "δ": 4,
    "ε": 5,
    "ϛ": 6,
    "ζ": 7,
    "η": 8,
    "θ": 9,
    "ι": 10,
    "κ": 20,
    "λ": 30,
    "μ": 40,
    "ν": 50,
    "ξ": 60,
    "ο": 70,
    "π": 80,
    "ϟ": 90,
    "ρ": 100,
    "σ": 200,
    "ς": 200,
    "τ": 300,
    "υ": 400,
    "φ": 500,
    "χ": 600,
    "ψ": 700,
    "ω": 800,
    "ϡ": 900,
}

GREEK_ORDINAL: dict[str, int] = {
    "Α": 1,
    "Β": 2,
    "Γ": 3,
    "Δ": 4,
    "Ε": 5,
    "Ζ": 6,
    "Η": 7,
    "Θ": 8,
    "Ι": 9,
    "Κ": 10,
    "Λ": 11,
    "Μ": 12,
    "Ν": 13,
    "Ξ": 14,
    "Ο": 15,
    "Π": 16,
    "Ρ": 17,
    "Σ": 18,
    "Τ": 19,
    "Υ": 20,
    "Φ": 21,
    "Χ": 22,
    "Ψ": 23,
    "Ω": 24,
    "α": 1,
    "β": 2,
    "γ": 3,
    "δ": 4,
    "ε": 5,
    "ζ": 6,
    "η": 7,
    "θ": 8,
    "ι": 9,
    "κ": 10,
    "λ": 11,
    "μ": 12,
    "ν": 13,
    "ξ": 14,
    "ο": 15,
    "π": 16,
    "ρ": 17,
    "σ": 18,
    "ς": 18,
    "τ": 19,
    "υ": 20,
    "φ": 21,
    "χ": 22,
    "ψ": 23,
    "ω": 24,
}

_STRONGS_RE = re.compile(r"^([HG])(\d+)$", re.I)


def normalize_strongs(raw: str) -> str | None:
    text = str(raw or "").strip().upper()
    if not text:
        return None
    m = _STRONGS_RE.match(text.replace(" ", ""))
    if not m:
        return None
    return f"{m.group(1).upper()}{int(m.group(2))}"


def language_from_strongs(strongs: str) -> str:
    return "hebrew" if strongs.startswith("H") else "greek"


def _strip_combining(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def prepare_lemma_for_gematria(lemma: str, language: str) -> str:
    text = _strip_combining(str(lemma or "").strip())
    if language == "greek":
        text = text.split(",")[0].strip()
        text = re.sub(r"[^Α-Ωα-ωϚϛϞϟϠϡ]", "", text)
    else:
        text = re.sub(r"[^א-ת]", "", text)
    return text


def _sum_table(text: str, table: dict[str, int]) -> int:
    return sum(table[ch] for ch in text if ch in table)


def _digital_root(n: int) -> int:
    value = abs(int(n))
    while value > 9:
        value = sum(int(d) for d in str(value))
    return value


def compute_hebrew_gematria(text: str) -> dict[str, int]:
    return {
        "mispar_hechrachi": _sum_table(text, HEBREW_HECHRACHI),
        "mispar_katan": _sum_table(text, HEBREW_KATAN),
        "mispar_siduri": _sum_table(text, HEBREW_SIDURI),
    }


def compute_greek_gematria(text: str) -> dict[str, int]:
    standard = _sum_table(text, GREEK_STANDARD)
    return {
        "isopsephy_standard": standard,
        "isopsephy_ordinal": _sum_table(text, GREEK_ORDINAL),
        "isopsephy_reduced": _digital_root(standard),
    }


def compute_gematria_for_lemma(lemma: str, language: str) -> tuple[str, dict[str, int]]:
    prepared = prepare_lemma_for_gematria(lemma, language)
    if language == "hebrew":
        return prepared, compute_hebrew_gematria(prepared)
    return prepared, compute_greek_gematria(prepared)


def slkm_vector_from_gematria(gematria: dict[str, int], language: str) -> dict[str, Any]:
    if language == "hebrew":
        meta = {
            "raw_combined_sum": int(gematria.get("mispar_hechrachi") or 0),
            "compressed_combined_sum": int(gematria.get("mispar_katan") or 0),
            "reconstructed_combined_sum": int(gematria.get("mispar_siduri") or 0),
        }
    else:
        meta = {
            "raw_combined_sum": int(gematria.get("isopsephy_standard") or 0),
            "compressed_combined_sum": int(gematria.get("isopsephy_reduced") or 0),
            "reconstructed_combined_sum": int(gematria.get("isopsephy_ordinal") or 0),
        }
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    return {
        "gematria_metadata": meta,
        "vector_4d": bridge.get("vector_4d") or {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        "kernel_recipe_id": KERNEL_RECIPE_ID,
        "lookup_only": True,
        "prophecy_claims": False,
    }
