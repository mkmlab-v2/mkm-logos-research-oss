#!/usr/bin/env python3
"""Forbidden reintro guard for 3-lens / Absolute Balance improvement wave.

Asserts: no horizon-role prediction remap · no lens→Final weight · no B→A from this wave.
Also scans agent-facing prose for affirmative 「성경=거시/명리=중기/사상=단기」 reintro
(unless the same line carries a deprecation marker).

  py scripts/check_mkm_three_lens_forbidden_reintro_guard_v1.py --strict
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/mkm_three_lens_forbidden_reintro_guard_v1_latest.json"
HORIZON = ROOT / "docs/final/artifacts/three_lens_horizon_empirical_eval_v2_latest.json"
BRIEF = ROOT / "docs/final/artifacts/commander_market_brief_v1_latest.json"
AB = ROOT / "docs/final/artifacts/absolute_balance_conflict_state_v1_latest.json"

# Agent-facing inject surfaces that previously re-taught the falsified mapping.
AGENT_FACING_SCAN = (
    ROOT / ".cursor/rules/central-agent-memory.mdc",
    ROOT / "CLAUDE.md",
    ROOT / "AGENTS.md",
    ROOT / "docs/final/AGENTS_REFERENCE_V1.md",
    ROOT / "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
    ROOT / "docs/final/LENS_UTILIZATION_CHARTER_V1.md",
    ROOT / "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
    ROOT / "docs/final/JEMA_LENS_ROLE_HYPOTHESIS_STATUS_V1.md",
    ROOT / "docs/final/MYEONGRI_INSIGHT_SSOT.md",
    ROOT / "scripts/build_mkm_chat_resume_pack_v1.py",
    ROOT / "docs/final/artifacts/universal_multi_res_plugin_registry_v1_latest.json",
    ROOT / "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json",
    ROOT / "docs/final/artifacts/jema_os_sasang_kernel_freeze_v1_latest.json",
    ROOT / "docs/final/artifacts/ollama_mkm_shallow_router_modelfile_v1.txt",
)

# Affirmative role-horizon fragments (prediction remap language).
_AFFIRM_PATTERNS = (
    re.compile(r"명리\s*[=：:]\s*`?중기"),
    re.compile(r"사상\s*[=：:]\s*`?단기"),
    re.compile(r"성경\s*[=：:]\s*`?거시"),
    re.compile(r"역할은\s*성경\s*=\s*`?거시"),
    re.compile(r"\*\*역할\s*고정\*\*"),
    re.compile(r"렌즈\s*역할\s*계약:\s*성경\s*=\s*거시"),
)

# Same-line markers that mean "citing the discarded myth", not reintroducing it.
_DEPRECATION_MARKERS = (
    "폐기",
    "falsif",
    "deprecated",
    "0/5",
    "alignment_pass",
    "hypothesis_supported",
    "예측 역할 매핑 폐기",
    "예측 매핑은",
    "예측 라벨",
    "예측매핑",
    "예측 호라이즌",
    "예측호라이즌",
    "no longer",
    "do not map",
    "금지",
    "아님",
    "ARCHIVED_DISCARDED",
    "DISCARDED",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _line_has_deprecation(line: str) -> bool:
    low = line.lower()
    for m in _DEPRECATION_MARKERS:
        if m.lower() in low:
            return True
    return False


def scan_agent_facing_prose() -> list[str]:
    """Return error codes for affirmative horizon-role language without deprecation."""
    errs: list[str] = []
    for path in AGENT_FACING_SCAN:
        if not path.is_file():
            errs.append(f"missing_agent_facing:{path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        for i, line in enumerate(text.splitlines(), start=1):
            if not any(p.search(line) for p in _AFFIRM_PATTERNS):
                continue
            # Deprecation markers apply to the SAME LINE only (no adjacent-line window).
            if _line_has_deprecation(line):
                continue
            errs.append(f"agent_facing_horizon_role_reintro:{rel}:{i}")
    return errs


def check() -> dict[str, Any]:
    errs: list[str] = []

    if HORIZON.is_file():
        h = json.loads(HORIZON.read_text(encoding="utf-8-sig"))
        # nested under v1_direction_eval.alignment_verdict in current artifact
        verdict = ((h.get("v1_direction_eval") or {}).get("alignment_verdict") or {})
        supported = h.get("hypothesis_supported")
        if supported is None:
            supported = verdict.get("hypothesis_supported")
        if supported is None:
            supported = h.get("hypothesis_supported_v2")
        if supported is True:
            errs.append("horizon_role_prediction_remapped_forbidden")
        elif supported is False:
            pass  # expected discarded mapping
        else:
            errs.append("horizon_hypothesis_supported_flag_missing")
        if verdict.get("lenses_alignment_pass") not in (0, None) and supported is True:
            errs.append("horizon_alignment_pass_with_supported_forbidden")
        if h.get("promotion_to_a_track_allowed") is True:
            errs.append("horizon_eval_must_not_promote_a")
    else:
        errs.append("missing:three_lens_horizon_empirical_eval_v2")

    if BRIEF.is_file():
        b = json.loads(BRIEF.read_text(encoding="utf-8-sig"))
        fa = b.get("final_action") or {}
        if fa.get("uses_lens_direction_weight") is not False:
            errs.append("brief_lens_to_final_weight_forbidden")
        if fa.get("uses_religious_trading_weight") is not False:
            errs.append("brief_religious_weight_forbidden")
        non = b.get("non_claims") or []
        for need in ("no_track_a_promotion", "no_b_to_a_auto_bridge", "no_send_unlock"):
            if need not in non:
                errs.append(f"brief_non_claims_missing:{need}")
    else:
        errs.append("missing:commander_market_brief")

    if AB.is_file():
        ab = json.loads(AB.read_text(encoding="utf-8-sig"))
        if ab.get("vector_merge_forbidden") is not True:
            errs.append("ab_vector_merge_must_forbidden")
        if (ab.get("final_action") or {}).get("source") != "field_plus_ops_gates":
            errs.append("ab_final_must_field_plus_ops")
        if ab.get("not_fifth_ai") is not True:
            errs.append("ab_not_fifth_ai")
    else:
        errs.append("missing:absolute_balance")

    prose_errs = scan_agent_facing_prose()
    errs.extend(prose_errs)

    return {
        "schema": "mkm_three_lens_forbidden_reintro_guard_v1",
        "version": "1.1.1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "guards": {
            "no_horizon_role_prediction_remapping": True,
            "no_lens_to_final_weight": True,
            "no_b_to_a_from_this_wave": True,
            "absolute_balance_is_state_not_fifth_ai": True,
            "no_agent_facing_horizon_role_reintro": True,
        },
        "agent_facing_scan_paths": [p.relative_to(ROOT).as_posix() for p in AGENT_FACING_SCAN],
        "errors": errs,
        "ok": len(errs) == 0,
        "reproduce": "py scripts/check_mkm_three_lens_forbidden_reintro_guard_v1.py --strict",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    doc = check()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(args.out), "errors": doc["errors"]}, ensure_ascii=False))
    if args.strict and not doc["ok"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
