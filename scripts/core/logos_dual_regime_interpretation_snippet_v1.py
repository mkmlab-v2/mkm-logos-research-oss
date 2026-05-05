"""Deterministic extraction/validation for logos_dual_regime interpretation brief lines.

SSOT rules artifact: docs/final/artifacts/LOGOS_DUAL_REGIME_INTERPRETATION_SNIPPET_RULES_V1.json

Consumers (multilens thin harness, ops brief builders) should surface interpretation_snippet
for 1-page operational briefs; full interpretation remains audit-only.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

RULES_REL = "docs/final/artifacts/LOGOS_DUAL_REGIME_INTERPRETATION_SNIPPET_RULES_V1.json"

# Known segment heads produced by projects/bitcoin-trading/src/integration/dual_regime_api.py
# plus optional GPU logos segments and state clamp notes (single outer segments).
_SEGMENT_HEAD = re.compile(
    r"^(gate_profile|PSI|bible_risk|stress|cap|logos_resonance|logos_delta|logos_skip|"
    r"state_clamp|state_clamp_skip|bulkhead)="
)


def load_rules(workspace_root: Path) -> dict[str, Any]:
    p = workspace_root / RULES_REL
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


PREFIX = "dual_regime: "


def validate_dual_regime_interpretation(full: str) -> tuple[bool, str | None]:
    """Return (ok, error_reason). Empty string is invalid.

    Segments are split on ``"; "`` to match ``dual_regime_api`` (``"; ".join(parts)``).
    Inner semicolons without following space remain inside one segment (e.g. state_clamp).
    """
    s = str(full).strip()
    if not s:
        return False, "empty"
    if not s.startswith(PREFIX):
        return False, "missing_dual_regime_prefix"
    body = s[len(PREFIX) :]
    if not body.strip():
        return False, "empty_body"
    segments = [x.strip() for x in body.split("; ") if x.strip()]
    if not segments:
        return False, "no_segments"
    for seg in segments:
        if not _SEGMENT_HEAD.match(seg):
            return False, f"disallowed_segment:{seg[:48]}"
    return True, None


def clip_snippet(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return "…"
    return text[: max_chars - 1].rstrip() + "…"


def build_interpretation_snippet(
    full_interpretation: str,
    *,
    workspace_root: Path | None = None,
    max_chars: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Build brief-safe interpretation_snippet from evaluate_dual_regime_and_market_shock.interpretation.

    On validation failure, emit deterministic placeholder + sha256 prefix of full string for audit lookup.
    """
    rules = load_rules(workspace_root) if workspace_root else {}
    cap = int(max_chars if max_chars is not None else rules.get("snippet_max_chars", 480))
    cap = max(64, min(cap, 4096))

    ok, err = validate_dual_regime_interpretation(full_interpretation)
    meta: dict[str, Any] = {
        "validation_ok": ok,
        "validation_error": err,
        "snippet_max_chars": cap,
        "rules_ref": RULES_REL,
    }

    if ok:
        clipped = clip_snippet(str(full_interpretation).strip(), cap)
        meta["snippet_source"] = "validated_clip"
        return clipped, meta

    digest = hashlib.sha256(str(full_interpretation).encode("utf-8")).hexdigest()[:16]
    fallback = (
        f"dual_regime: interpretation_snippet_fallback;reason={err};audit_sha256_prefix={digest}"
    )
    clipped_fb = clip_snippet(fallback, cap)
    meta["snippet_source"] = "fallback_noncompliant"
    return clipped_fb, meta
