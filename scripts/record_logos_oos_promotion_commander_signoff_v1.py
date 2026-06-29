#!/usr/bin/env python3
"""Record commander sign-off for Logos OOS / birth overlay review (default: keep SSOT)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "reports/logos_birth_overlay_promotion_review_draft_v1_latest.json"
SIGNOFF_OUT = ROOT / "docs/final/artifacts/logos_oos_promotion_commander_signoff_v1_latest.json"
APPENDIX_OUT = ROOT / "docs/final/artifacts/logos_sidecar_research_appendix_v1_latest.json"
SSOT_GATE = ROOT / "docs/final/artifacts/prophecy_logos_revalidation_oos_gate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _build_appendix(draft: dict[str, Any], compare: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "logos_sidecar_research_appendix_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "logos_oos_gate_ssot": str(SSOT_GATE.relative_to(ROOT)).replace("\\", "/"),
        "ssot_oos_hit": (draft.get("current_ssot") or {}).get("oos_hit"),
        "commander_decision": "keep_ssot_option_a",
        "approved_research_variants": [
            {
                "label": "hybrid_ext",
                "role": "near_golden_confirm_window",
                "pointer": "reports/logos_oos_kospi_hybrid_ext_v1_latest.json",
            },
            {
                "label": "birth_sw025_band006",
                "role": "hypothesis_sweep_not_ssot",
                "pointer": "reports/logos_oos_kospi_birth_overlay_sw025_band006_v1_latest.json",
                "holdout_promotion_candidate": False,
            },
            {
                "label": "sparse_blind_session_fill",
                "role": "blind_window_fill_rejected",
                "pointer": "reports/logos_oos_kospi_sparse_blind_session_fill_v1_latest.json",
            },
        ],
        "variant_compare_pointer": draft.get("variant_compare_pointer"),
        "variants_summary": compare.get("variants"),
        "messaging_ko": (
            "성경 D·Telegram·성숙도는 SSOT 0.565217 고정. "
            "hybrid/birth 수치는 [HYPO] 연구각주·본 부록만."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--approved-option",
        choices=("A", "B", "C"),
        default="A",
        help="A=keep SSOT (default). B=research appendix only. C=replace SSOT (discouraged).",
    )
    ap.add_argument("--notes", default="", help="Optional commander note")
    args = ap.parse_args()

    if not DRAFT.is_file():
        raise SystemExit(f"Missing draft: {DRAFT}")

    draft = _read(DRAFT)
    compare_path = ROOT / str(draft.get("variant_compare_pointer") or "reports/logos_oos_sidecar_variant_compare_v1_latest.json")
    compare = _read(compare_path) if compare_path.is_file() else {}

    opt = args.approved_option.upper()
    ssot_touched = False
    if opt == "C":
        birth_report = ROOT / str(
            (draft.get("candidate_birth_overlay_sw025_band006") or {}).get("full_oos_report")
            or "reports/logos_oos_kospi_birth_overlay_sw025_band006_v1_latest.json"
        )
        if not birth_report.is_file():
            raise SystemExit(f"Option C requires birth OOS report: {birth_report}")
        ssot_touched = True
        SSOT_GATE.write_text(birth_report.read_text(encoding="utf-8-sig"), encoding="utf-8")

    draft["status"] = (
        "approved_keep_ssot"
        if opt == "A"
        else ("approved_research_appendix_only" if opt == "B" else "approved_ssot_replaced_birth")
    )
    draft["apply_forbidden"] = opt != "C"
    draft["approved_option"] = opt
    draft["approved_at_utc"] = _now()
    draft["approval_block"] = {
        "commander_signoff": True,
        "legal_counsel_signoff": draft.get("approval_block", {}).get("legal_counsel_signoff", False),
        "notes": args.notes or "지휘관 승인(채팅)",
    }
    draft["ssot_gate_modified"] = ssot_touched
    DRAFT.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    signoff = {
        "schema": "logos_oos_promotion_commander_signoff_v1",
        "signed_at_utc": _now(),
        "approved_option": opt,
        "decision_ko": {
            "A": "SSOT 유지 — prophecy_logos_revalidation_oos_gate_latest.json 미변경",
            "B": "연구 부록만 공식화 — SSOT 유지",
            "C": "birth OOS로 SSOT gate 교체(비권장 경로)",
        }.get(opt, ""),
        "ssot_path": str(SSOT_GATE.relative_to(ROOT)).replace("\\", "/"),
        "ssot_modified": ssot_touched,
        "draft_pointer": str(DRAFT.relative_to(ROOT)).replace("\\", "/"),
        "research_only": opt != "C",
        "track_a_live_trading_auto_go": False,
    }
    SIGNOFF_OUT.parent.mkdir(parents=True, exist_ok=True)
    SIGNOFF_OUT.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    appendix = _build_appendix(draft, compare)
    APPENDIX_OUT.write_text(json.dumps(appendix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(signoff, ensure_ascii=False, indent=2))
    print(f"WROTE: {SIGNOFF_OUT.resolve()}")
    print(f"WROTE: {APPENDIX_OUT.resolve()}")
    print(f"UPDATED: {DRAFT.resolve()}")
    if opt == "A":
        print("SSOT unchanged (golden 0.565217).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
