"""Pack 0-B DoD §2.4: high-risk therapeutic / neuroscience claim phrases absent from code paths.

Scopes **machine-facing** Pack 0-B surfaces only (not `LORA_PACK_V0_DOD_V1.md`, which meta-lists
forbidden wording). Aligns with `docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md` spirit
and `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` — marketing copy still needs
human/legal review; this test blocks accidental insertion into schema/prep/eval artifacts.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# Substrings that must not appear in Pack 0-B training/schema/prep surfaces (KR + EN).
_FORBIDDEN_SUBSTRINGS: tuple[str, ...] = (
    "신경과학적으로 증명",
    "뇌 기반으로 성과 보장",
    "호르몬 치료 효능",
    "뇌신경으로 치료",
    "장내미생물로 치료",
    "neuroscience proves cure",
    "clinically proven to cure",
)

_SURFACES: tuple[Path, ...] = (
    _ROOT / "docs/final/schemas/myeongri_deterministic_lora_golden_set_v1.schema.json",
    _ROOT / "docs/final/artifacts/myeongri_deterministic_lora_model_profiles_v1.json",
    _ROOT / "scripts/prep_myeongri_deterministic_lora_golden_v1.py",
    _ROOT / "scripts/build_myeongri_deterministic_lora_golden_bulk_v1.py",
    _ROOT / "scripts/eval_myeongri_deterministic_lora_golden_fit_v1.py",
    _ROOT / "tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl",
    _ROOT / "storage/adapters/myeongri_deterministic_lora_v0/.gitkeep",
)


def test_pack_surfaces_exist() -> None:
    missing = [str(p.relative_to(_ROOT)) for p in _SURFACES if not p.is_file()]
    assert not missing, f"missing Pack 0-B surfaces: {missing}"


def test_no_forbidden_therapeutic_claim_phrases_in_pack_surfaces() -> None:
    for path in _SURFACES:
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for bad in _FORBIDDEN_SUBSTRINGS:
            needle = bad.lower() if bad.isascii() else bad
            hay = lower if bad.isascii() else text
            assert needle not in hay, f"{path.relative_to(_ROOT)}: forbidden substring {bad!r}"
