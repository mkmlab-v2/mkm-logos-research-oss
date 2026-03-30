from __future__ import annotations

from dataclasses import dataclass


# Hebrew and Greek baseline mappings for additive gematria checks.
_HEBREW_MAP: dict[str, int] = {
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
    "ך": 20,
    "ל": 30,
    "מ": 40,
    "ם": 40,
    "נ": 50,
    "ן": 50,
    "ס": 60,
    "ע": 70,
    "פ": 80,
    "ף": 80,
    "צ": 90,
    "ץ": 90,
    "ק": 100,
    "ר": 200,
    "ש": 300,
    "ת": 400,
}

_GREEK_MAP: dict[str, int] = {
    "α": 1,
    "β": 2,
    "γ": 3,
    "δ": 4,
    "ε": 5,
    "ϛ": 6,
    "ς": 200,  # final sigma defaults to sigma value in additive mode
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
    "τ": 300,
    "υ": 400,
    "φ": 500,
    "χ": 600,
    "ψ": 700,
    "ω": 800,
    "ϡ": 900,
}


@dataclass(frozen=True)
class GematriaScore:
    hebrew_sum: int
    greek_sum: int
    combined_sum: int
    hebrew_chars: int
    greek_chars: int

    def to_dict(self) -> dict[str, int]:
        return {
            "hebrew_sum": self.hebrew_sum,
            "greek_sum": self.greek_sum,
            "combined_sum": self.combined_sum,
            "hebrew_chars": self.hebrew_chars,
            "greek_chars": self.greek_chars,
        }


def _score_text(text: str) -> GematriaScore:
    hebrew_sum = 0
    greek_sum = 0
    hebrew_chars = 0
    greek_chars = 0
    for ch in text:
        if ch in _HEBREW_MAP:
            hebrew_sum += _HEBREW_MAP[ch]
            hebrew_chars += 1
            continue
        low = ch.lower()
        if low in _GREEK_MAP:
            greek_sum += _GREEK_MAP[low]
            greek_chars += 1
    return GematriaScore(
        hebrew_sum=hebrew_sum,
        greek_sum=greek_sum,
        combined_sum=hebrew_sum + greek_sum,
        hebrew_chars=hebrew_chars,
        greek_chars=greek_chars,
    )


def build_gematria_metadata(*, raw_text: str, compressed_text: str, reconstructed_text: str) -> dict[str, int]:
    raw = _score_text(raw_text)
    comp = _score_text(compressed_text)
    rec = _score_text(reconstructed_text)
    return {
        "raw_combined_sum": raw.combined_sum,
        "compressed_combined_sum": comp.combined_sum,
        "reconstructed_combined_sum": rec.combined_sum,
        "raw_hebrew_sum": raw.hebrew_sum,
        "raw_greek_sum": raw.greek_sum,
        "compressed_hebrew_sum": comp.hebrew_sum,
        "compressed_greek_sum": comp.greek_sum,
        "reconstructed_hebrew_sum": rec.hebrew_sum,
        "reconstructed_greek_sum": rec.greek_sum,
        "raw_hebrew_chars": raw.hebrew_chars,
        "raw_greek_chars": raw.greek_chars,
        "compressed_hebrew_chars": comp.hebrew_chars,
        "compressed_greek_chars": comp.greek_chars,
        "reconstructed_hebrew_chars": rec.hebrew_chars,
        "reconstructed_greek_chars": rec.greek_chars,
    }
