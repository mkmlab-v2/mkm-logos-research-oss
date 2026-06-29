"""DeepNSM HF Ollama inference lib smoke (offline)."""

from __future__ import annotations

from scripts.deepnsm_hf_ollama_inference_lib_v1 import (
    build_ollama_hint_prompt,
    prepare_gematria_index,
    resolve_probe_via_ollama_assist,
)
from scripts.deepnsm_shadow_explication_lib_v1 import DEFAULT_GEMATRIA_LEXICON


def test_build_ollama_hint_prompt_has_probes() -> None:
    prompt = build_ollama_hint_prompt(
        {
            "prime_en": "good",
            "lang_probes": {"en": "good", "greek": "agathos", "hebrew": "tov"},
        }
    )
    assert "good" in prompt
    assert "agathos" in prompt
    assert "tov" in prompt
    assert "greek_gloss_en" in prompt


def test_resolve_probe_via_ollama_assist_uses_hints() -> None:
    rows, index = prepare_gematria_index(str(DEFAULT_GEMATRIA_LEXICON.resolve()))
    hints = {"greek_gloss_en": "good", "hebrew_gloss_en": "good", "ok": True}
    greek = resolve_probe_via_ollama_assist(
        "agathos",
        "greek",
        index,
        rows,
        ollama_hints=hints,
        prime_en="good",
        en_hint="good",
    )
    assert greek.get("resolution_backend") == "ollama_local_weights_v1"
    assert greek.get("ollama_gloss_hint") == "good"
