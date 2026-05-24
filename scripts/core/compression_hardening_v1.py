#!/usr/bin/env python3
"""Enterprise compression hardening hooks (M1–M2): mask, gatekeeper, circuit breaker, LLM params."""
from __future__ import annotations

import hashlib
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_CONFIG = ART / "compression_enterprise_hardening_config_v1.json"

NUMBER_SPAN_RE = re.compile(
    r"(?<!\w)(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?:%|원|만|억|조)?(?!\w)"
)
NEGATION_RE = re.compile(
    r"(?i)(?:^|[\s,.;:!?(\[])"
    r"(?:not|no|never|none|without|cannot|can't|won't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't"
    r"|없|안|못|아니|불|비|미|무|절|금지|deny|denied|reject)"
    r"(?:$|[\s,.;:!?)\]])"
)


@lru_cache(maxsize=1)
def _config_doc() -> dict[str, Any]:
    raw_path = os.environ.get("COMPRESSION_HARDENING_CONFIG_PATH", "").strip()
    path = Path(raw_path) if raw_path else DEFAULT_CONFIG
    if not path.is_absolute():
        path = ROOT / path
    if path.is_file():
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
            return doc if isinstance(doc, dict) else {}
        except Exception:
            return {}
    return {
        "schema": "compression_enterprise_hardening_config_v1",
        "gatekeeper_bypass_max_tokens": 4000,
        "llm_decode": {"temperature": 0.0, "seed": 42},
        "circuit_breaker": {"min_jaccard": 0.75, "force_identity_on_eval_error": True},
    }


def gatekeeper_bypass_max_tokens() -> int:
    doc = _config_doc()
    try:
        return max(0, int(doc.get("gatekeeper_bypass_max_tokens", 4000)))
    except (TypeError, ValueError):
        return 4000


def should_bypass_compression(token_in: int) -> bool:
    """Below threshold: skip compression hot path (identity pass-through)."""
    return token_in < gatekeeper_bypass_max_tokens()


def llm_decode_params() -> dict[str, Any]:
    doc = _config_doc()
    block = doc.get("llm_decode") if isinstance(doc.get("llm_decode"), dict) else {}
    temp = block.get("temperature", 0.0)
    seed = block.get("seed", 42)
    try:
        temp_f = float(temp)
    except (TypeError, ValueError):
        temp_f = 0.0
    try:
        seed_i = int(seed)
    except (TypeError, ValueError):
        seed_i = 42
    return {"temperature": temp_f, "seed": seed_i, "do_sample": temp_f > 0.0}


def extract_mask_must_keep(text: str) -> tuple[set[str], dict[str, Any]]:
    """Numbers and negation spans → must_keep terms (pre-compress bypass)."""
    terms: set[str] = set()
    for m in NUMBER_SPAN_RE.finditer(text):
        s = m.group(0).strip()
        if s:
            terms.add(s)
    for m in NEGATION_RE.finditer(text):
        s = m.group(0).strip()
        if len(s) >= 2:
            terms.add(s)
    meta = {
        "mask_applied": bool(terms),
        "mask_term_count": len(terms),
        "mask_sample": sorted(terms)[:12],
    }
    return terms, meta


def circuit_breaker_min_jaccard() -> float:
    doc = _config_doc()
    cb = doc.get("circuit_breaker") if isinstance(doc.get("circuit_breaker"), dict) else {}
    try:
        return float(cb.get("min_jaccard", 0.75))
    except (TypeError, ValueError):
        return 0.75


def force_identity_on_eval_error() -> bool:
    doc = _config_doc()
    cb = doc.get("circuit_breaker") if isinstance(doc.get("circuit_breaker"), dict) else {}
    return bool(cb.get("force_identity_on_eval_error", True))


def should_circuit_break_report(report: dict[str, Any] | None) -> tuple[bool, list[str]]:
    """True → use identity / decision_fallback instead of live metrics."""
    reasons: list[str] = []
    if not isinstance(report, dict):
        return True, ["report_missing"]
    cm = report.get("compression_metrics") or {}
    if not isinstance(cm, dict):
        return True, ["compression_metrics_missing"]
    jac = cm.get("avg_jaccard")
    if jac is None:
        qg = report.get("quality_gate") or {}
        if isinstance(qg, dict):
            jac = qg.get("avg_jaccard")
    try:
        jac_f = float(jac) if jac is not None else None
    except (TypeError, ValueError):
        jac_f = None
    if jac_f is None:
        return False, []
    if jac_f < circuit_breaker_min_jaccard():
        reasons.append(f"jaccard_below_min:{jac_f:.4f}")
        return True, reasons
    return False, reasons


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
