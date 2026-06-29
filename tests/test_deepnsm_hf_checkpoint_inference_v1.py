"""DeepNSM HF checkpoint inference lib smoke (offline)."""

from __future__ import annotations

from scripts.deepnsm_hf_checkpoint_inference_lib_v1 import (
    build_checkpoint_prompt,
    prepare_gematria_index,
    resolve_probe_via_checkpoint_assist,
)
from scripts.deepnsm_shadow_explication_lib_v1 import DEFAULT_GEMATRIA_LEXICON


def test_build_checkpoint_prompt_has_word_and_examples() -> None:
    prompt = build_checkpoint_prompt(
        {
            "prime_en": "good",
            "lang_probes": {"en": "good", "greek": "agathos", "hebrew": "tov"},
        }
    )
    assert "Word: good" in prompt
    assert "Examples:" in prompt
    assert "Paraphrase:" in prompt


def test_resolve_probe_via_checkpoint_assist_uses_explication() -> None:
    rows, index = prepare_gematria_index(str(DEFAULT_GEMATRIA_LEXICON.resolve()))
    hints = {
        "greek_gloss_en": "something good can happen",
        "hebrew_gloss_en": "something good can happen",
        "explication_preview": "something good can happen to someone",
        "ok": True,
    }
    greek = resolve_probe_via_checkpoint_assist(
        "agathos",
        "greek",
        index,
        rows,
        checkpoint_hints=hints,
        prime_en="good",
        en_hint="good",
    )
    assert greek.get("resolution_backend") == "deepnsm_hf_checkpoint_v1"
    assert greek.get("checkpoint_gloss_hint")
