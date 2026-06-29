#!/usr/bin/env python3
"""DeepNSM HF Ollama local-weights assist — LLM gloss hints + gematria index [HYPO]."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from scripts.deepnsm_shadow_explication_lib_v1 import (
    build_translit_index,
    load_gematria_rows,
    normalize_latin_translit,
    resolve_probe_via_gematria,
)

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma4:e2b"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


def ollama_host() -> str:
    _load_dotenv()
    return (os.getenv("MKM_DEEPNSM_HF_OLLAMA_HOST") or os.getenv("OLLAMA_HOST") or DEFAULT_HOST).rstrip(
        "/"
    ).replace("/v1", "")


def ollama_model(override: str | None = None) -> str:
    _load_dotenv()
    if override:
        return override
    return (
        os.getenv("MKM_DEEPNSM_HF_OLLAMA_MODEL")
        or os.getenv("OLLAMA_MODEL")
        or DEFAULT_MODEL
    )


def ollama_reachable(host: str | None = None, *, timeout: int = 5) -> bool:
    host = host or ollama_host()
    try:
        req = urllib.request.Request(f"{host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            json.loads(resp.read().decode("utf-8"))
        return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return False


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    if start < 0:
        return None
    depth = 0
    for idx in range(start, len(cleaned)):
        ch = cleaned[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                chunk = cleaned[start : idx + 1]
                try:
                    parsed = json.loads(chunk)
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def ollama_generate(
    prompt: str,
    *,
    host: str | None = None,
    model: str | None = None,
    timeout: int = 120,
    num_predict: int = 256,
) -> tuple[str, float]:
    host = host or ollama_host()
    model = model or ollama_model()
    url = f"{host}/api/generate"
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"num_predict": num_predict, "temperature": 0.0, "top_p": 0.1},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    import time

    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    latency = time.perf_counter() - start
    return str(doc.get("response") or "").strip(), latency


def build_ollama_hint_prompt(sample: dict[str, Any]) -> str:
    lang = sample.get("lang_probes") if isinstance(sample.get("lang_probes"), dict) else {}
    prime = str(sample.get("prime_en") or "")
    en = str(lang.get("en") or prime)
    greek = str(lang.get("greek") or "")
    hebrew = str(lang.get("hebrew") or "")
    return (
        "You assist NSM (Natural Semantic Metalanguage) cross-lingual lexicon research [HYPO].\n"
        f"NSM prime: {prime}\n"
        f"English probe: {en}\n"
        f"Greek transliteration probe: {greek}\n"
        f"Hebrew transliteration probe: {hebrew}\n\n"
        "Return JSON only with short English gloss hints for lexicon lookup:\n"
        '{"greek_gloss_en":"...", "hebrew_gloss_en":"..."}\n'
        "No theology. No prose outside JSON."
    )


def fetch_ollama_gloss_hints(
    sample: dict[str, Any],
    *,
    host: str | None = None,
    model: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    prompt = build_ollama_hint_prompt(sample)
    try:
        text, latency = ollama_generate(prompt, host=host, model=model, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)[:200], "latency_sec": None}
    parsed = _extract_json_object(text) or {}
    return {
        "ok": True,
        "latency_sec": round(latency, 4),
        "greek_gloss_en": str(parsed.get("greek_gloss_en") or parsed.get("greek") or "")[:200],
        "hebrew_gloss_en": str(parsed.get("hebrew_gloss_en") or parsed.get("hebrew") or "")[:200],
        "raw_preview": text[:300],
    }


def resolve_probe_via_ollama_assist(
    probe: str,
    lang: str,
    index: dict[tuple[str, str], list[dict[str, Any]]],
    rows: tuple[dict[str, Any], ...],
    *,
    ollama_hints: dict[str, Any],
    prime_en: str = "",
    en_hint: str = "",
) -> dict[str, Any]:
    lang_key = str(lang or "").strip().lower()
    gloss_key = f"{lang_key}_gloss_en"
    gloss = str(ollama_hints.get(gloss_key) or "")
    combined_hint = " ".join(x for x in (en_hint, gloss, prime_en) if x).strip()
    resolved = resolve_probe_via_gematria(probe, lang_key, index, rows, en_hint=combined_hint)
    resolved["resolution_backend"] = "ollama_local_weights_v1"
    resolved["ollama_gloss_hint"] = gloss[:120] if gloss else ""
    if resolved.get("resolution", "").startswith("gematria"):
        resolved["resolution"] = resolved["resolution"].replace("gematria", "ollama_assist", 1)
    return resolved


def build_hf_ollama_explication_record(
    sample: dict[str, Any],
    *,
    pair_index: int,
    rows: tuple[dict[str, Any], ...],
    index: dict[tuple[str, str], list[dict[str, Any]]],
    ollama_hints: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    lang = sample.get("lang_probes") if isinstance(sample.get("lang_probes"), dict) else {}
    prime_en = str(sample.get("prime_en") or "")
    en_hint = str(lang.get("en") or prime_en or "")
    greek = resolve_probe_via_ollama_assist(
        str(lang.get("greek") or ""),
        "greek",
        index,
        rows,
        ollama_hints=ollama_hints,
        prime_en=prime_en,
        en_hint=en_hint,
    )
    hebrew = resolve_probe_via_ollama_assist(
        str(lang.get("hebrew") or ""),
        "hebrew",
        index,
        rows,
        ollama_hints=ollama_hints,
        prime_en=prime_en,
        en_hint=en_hint,
    )
    explication = (
        f"[HYPO][OLLAMA] NSM prime '{prime_en}' — greek→"
        f"{greek.get('lemma_script') or greek.get('resolution')} "
        f"(strongs={greek.get('strongs') or 'n/a'}); hebrew→"
        f"{hebrew.get('lemma_script') or hebrew.get('resolution')} "
        f"(strongs={hebrew.get('strongs') or 'n/a'}). model={model}"
    )
    return {
        "schema": "deepnsm_hf_explication_ollama_v1",
        "pair_index": pair_index,
        "pair_id": f"{prime_en}::{sample.get('variant') or pair_index}",
        "prime_en": prime_en,
        "variant": sample.get("variant"),
        "control": sample.get("control"),
        "lang_probes": lang,
        "ollama_hints": {
            "greek_gloss_en": ollama_hints.get("greek_gloss_en"),
            "hebrew_gloss_en": ollama_hints.get("hebrew_gloss_en"),
            "latency_sec": ollama_hints.get("latency_sec"),
            "ok": ollama_hints.get("ok"),
        },
        "resolved_probes": {"greek": greek, "hebrew": hebrew},
        "explication_template": explication,
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "implementation_note": "Ollama local weights gloss-assist + gematria index — not arXiv DeepNSM HF 1B checkpoint",
    }


def prepare_gematria_index(lexicon_path: str) -> tuple[tuple[dict[str, Any], ...], dict[tuple[str, str], list[dict[str, Any]]]]:
    rows = load_gematria_rows(lexicon_path)
    return rows, build_translit_index(rows)


__all__ = [
    "ollama_host",
    "ollama_model",
    "ollama_reachable",
    "fetch_ollama_gloss_hints",
    "build_hf_ollama_explication_record",
    "prepare_gematria_index",
    "resolve_probe_via_ollama_assist",
]
