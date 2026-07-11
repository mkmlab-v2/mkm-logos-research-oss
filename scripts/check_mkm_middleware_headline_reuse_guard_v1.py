#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claim-A headline reuse guard + Blind prefer×side crosstab [research_only].

Nails Claude 1.6 residual: legacy 'Send pointers' must not ship alone without
counter-signal. Rev 1.7: prefer egress Hero frame for external/SEND paste;
usefulness claim for pointer arm remains challenged (plain_full > id_only).

  py scripts/check_mkm_middleware_headline_reuse_guard_v1.py
  py scripts/check_mkm_middleware_headline_reuse_guard_v1.py --check-file docs/final/artifacts/foo.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_middleware_llm_harness_lib_v1 import utc_now  # noqa: E402

ART = ROOT / "docs/final/artifacts"
OUT_CHECKLIST = ART / "mkm_middleware_headline_reuse_checklist_v1_latest.json"
OUT_CROSSTAB = ART / "mkm_middleware_blind_prefer_side_crosstab_v1_latest.json"
OUT_MIRROR = ROOT / "reports/mkm_middleware_headline_reuse_checklist_v1_latest.json"

# Legacy usefulness-flavored core (must not appear orphan)
HEADLINE_CORE = re.compile(
    r"Keep the corpus local\.\s*Send pointers",
    re.I,
)
# Rev 1.7 preferred external Hero (egress / security — not usefulness)
EGRESS_HERO_CORE = re.compile(
    r"What leaves your boundary:\s*pointers,\s*locked citations,\s*and a hard HOLD",
    re.I,
)
# At least one counter-signal marker near legacy reuse
COUNTER_MARKERS = (
    "Counter-signal",
    "plain_full",
    "id_only",
    "VALUE-PROP TENSION",
    "not endorsed by commander blind",
    "challenged, not proven",
    "buyer-facing headline usefulness",
    "Claim frame",
    "egress / security",
    "not a usefulness claim",
    "not sell",
)
EGRESS_FRAME_MARKERS = (
    "Claim frame",
    "egress / security",
    "What leaves your boundary",
    "not a usefulness claim",
    "usefulness-proven",
)


def _load(p: Path) -> dict[str, Any]:
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def build_crosstab() -> dict[str, Any]:
    filled = _load(ART / "mkm_middleware_blind_rubric_scores_filled_v1_latest.json")
    key = _load(ART / "mkm_middleware_blind_rubric_key_v1_latest.json")
    kb = {m["item_id"]: m for m in (key.get("map") or [])}
    # cells: (A_arm, prefer) -> count
    cells: Counter[tuple[str, str]] = Counter()
    for s in filled.get("scores") or []:
        m = kb.get(s.get("item_id")) or {}
        a_arm = str(m.get("A_arm") or "?")
        pref = str(s.get("prefer") or "").upper() or "?"
        cells[(a_arm, pref)] += 1

    # P(prefer A | A_arm=id_only) etc.
    def rate(arm: str, pref: str) -> dict[str, Any]:
        n_arm = sum(c for (a, _), c in cells.items() if a == arm)
        n_hit = cells.get((arm, pref), 0)
        return {
            "n_arm": n_arm,
            "n_prefer": n_hit,
            "rate": round(n_hit / max(1, n_arm), 4),
        }

    return {
        "schema": "mkm_middleware_blind_prefer_side_crosstab_v1",
        "version": "1.0.0",
        "generated_at_utc": utc_now(),
        "research_only": True,
        "n_scores": len(filled.get("scores") or []),
        "cells_A_arm_x_prefer": {
            f"A_arm={a}|prefer={p}": c for (a, p), c in sorted(cells.items())
        },
        "position_bias_probe": {
            "note_ko": (
                "If prefer-A rate differs sharply by A_arm, may be arm quality; "
                "if prefer-A is high for BOTH arms, suspect position bias toward label A."
            ),
            "prefer_A_given_A_is_id_only": rate("id_only", "A"),
            "prefer_A_given_A_is_plain_full": rate("plain_full", "A"),
            "prefer_B_given_A_is_id_only": rate("id_only", "B"),
            "prefer_B_given_A_is_plain_full": rate("plain_full", "B"),
        },
        "unblinded_prefer": _load(
            ART / "mkm_middleware_blind_rubric_ingest_v1_latest.json"
        ).get("prefer_counts"),
    }


def check_text(text: str, *, path: str) -> dict[str, Any]:
    has_headline = bool(HEADLINE_CORE.search(text))
    has_egress_hero = bool(EGRESS_HERO_CORE.search(text))
    has_counter = any(m.lower() in text.lower() for m in COUNTER_MARKERS)
    has_egress_frame = any(m.lower() in text.lower() for m in EGRESS_FRAME_MARKERS)
    orphan = has_headline and not has_counter
    return {
        "path": path,
        "has_headline_core": has_headline,
        "has_egress_hero_core": has_egress_hero,
        "has_counter_signal_marker": has_counter,
        "has_egress_frame_marker": has_egress_frame,
        "orphan_headline": orphan,
        "ok": not orphan,
    }


def write_checklist(extra_checks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    defaults = [
        str(ART / "mkm_middleware_l0_send_ready_onepager_v1_latest.md"),
        str(ART / "mkm_middleware_claim_a_claude_submit_pack_v1_latest.md"),
        str(ART / "mkm_middleware_claim_a_claude_rereview_pack_v1_latest.md"),
    ]
    checks = []
    for p in defaults:
        path = Path(p)
        if not path.is_file():
            checks.append({"path": p, "ok": False, "error": "missing"})
            continue
        checks.append(check_text(path.read_text(encoding="utf-8", errors="ignore"), path=p))
    if extra_checks:
        checks.extend(extra_checks)

    onepager_row = next(
        (c for c in checks if "l0_send_ready_onepager" in str(c.get("path") or "")),
        {},
    )
    egress_aligned = bool(
        onepager_row.get("has_egress_hero_core") and onepager_row.get("has_egress_frame_marker")
    )

    doc = {
        "schema": "mkm_middleware_headline_reuse_checklist_v1",
        "version": "1.1.0",
        "generated_at_utc": utc_now(),
        "research_only": True,
        "rule_ko": (
            "Legacy headline core 'Keep the corpus local. Send pointers' MUST NOT appear "
            "in external/SEND copy without an adjacent counter-signal marker "
            "(plain_full prefer / VALUE-PROP TENSION / Counter-signal / Claim frame). "
            "Rev 1.7 preferred Hero: egress boundary ('What leaves your boundary…') — "
            "not usefulness for pointer-only answers."
        ),
        "headline_core": "Keep the corpus local. Send pointers",
        "egress_hero_core": (
            "Keep the corpus local. What leaves your boundary: pointers, "
            "locked citations, and a hard HOLD — never the corpus itself."
        ),
        "counter_markers": list(COUNTER_MARKERS),
        "egress_frame_markers": list(EGRESS_FRAME_MARKERS),
        "egress_hero_aligned_on_onepager": egress_aligned,
        "checks": checks,
        "ok": all(c.get("ok") for c in checks if "error" not in c),
        "reproduce": [
            "py scripts/check_mkm_middleware_headline_reuse_guard_v1.py",
            "py scripts/check_mkm_middleware_headline_reuse_guard_v1.py --check-file <path>",
        ],
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_CHECKLIST.write_text(text, encoding="utf-8")
    OUT_MIRROR.write_text(text, encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-file", type=Path, action="append", default=[])
    ap.add_argument("--skip-crosstab", action="store_true")
    args = ap.parse_args()

    extras: list[dict[str, Any]] = []
    for fp in args.check_file:
        if not fp.is_file():
            print(f"ERR: missing {fp}", file=sys.stderr)
            return 1
        extras.append(
            check_text(fp.read_text(encoding="utf-8", errors="ignore"), path=str(fp))
        )

    if not args.skip_crosstab:
        ct = build_crosstab()
        OUT_CROSSTAB.write_text(json.dumps(ct, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {OUT_CROSSTAB}")
        probe = ct.get("position_bias_probe") or {}
        print(
            "position_bias_probe "
            f"P(A|A=id_only)={probe.get('prefer_A_given_A_is_id_only')} "
            f"P(A|A=plain)={probe.get('prefer_A_given_A_is_plain_full')}"
        )

    doc = write_checklist(extras or None)
    print(f"WROTE: {OUT_CHECKLIST}")
    print(f"headline_reuse_ok={doc.get('ok')}")
    for c in doc.get("checks") or []:
        if c.get("orphan_headline") or c.get("error"):
            print(f"FAIL: {c}")
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
