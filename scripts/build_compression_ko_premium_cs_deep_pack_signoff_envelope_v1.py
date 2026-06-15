#!/usr/bin/env python3
"""Build ko premium cs deep pack promotion signoff envelope (separate axes)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_GATE = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_gate_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_promotion_signoff_envelope_v1_latest.json"
EN_BUSINESS_SIGNOFF = ROOT / "docs/final/artifacts/compression_en_business_deep_pack_promotion_signoff_envelope_v1_latest.json"
SPEC = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_spec_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_envelope(*, gate_path: Path) -> dict[str, Any]:
    gate = _load(gate_path)
    summary = gate.get("summary") or {}
    catalog = gate.get("template_catalog") or {}
    row_count = int(catalog.get("row_count") or summary.get("case_count") or 0)
    exact_restore = int(summary.get("exact_restore_pass_count") or 0)
    mean_saving = float(summary.get("mean_saving_rate") or 0.0)
    return {
        "schema": "compression_ko_premium_cs_deep_pack_promotion_signoff_envelope_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "envelope_status": "draft_awaiting_commander",
        "vertical": "ko_premium_cs_turn",
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "gate_artifact": _rel(gate_path),
        "vertical_spec": _rel(SPEC),
        "separate_from_en_business_signoff": _rel(EN_BUSINESS_SIGNOFF),
        "guardrail_ko": (
            "ko premium cs deep pack twin gate는 CS_MASK template-catalog wire 전용. "
            "BIZ_MASK en business·ZF_MASK coding·wtt shortcap 헤드라인과 합선 금지 (FAIL-COMP-004). "
            "███ 마스크 토큰 exact-restore 필수."
        ),
        "guardrail_en": (
            "Ko premium CS deep pack twin gate applies to CS_MASK template-catalog wire only. "
            "Do not merge with BIZ_MASK en business, ZF_MASK coding pack, or wtt shortcap headlines. "
            "Masked tokens (███) must exact-restore."
        ),
        "fallback_spec": "docs/final/artifacts/compression_ko_premium_cs_deep_pack_fallback_spec_v1_latest.json",
        "signoff_checklist": "docs/final/artifacts/compression_ko_premium_cs_deep_pack_signoff_checklist_v1_latest.json",
        "signoff_checklist_builder": "scripts/build_compression_ko_premium_cs_deep_pack_signoff_checklist_v1.py",
        "promotion_gates_at_apply": {
            "roundtrip_path": "template_catalog_wire_v1",
            "wire_family": "CS_MASK",
            "template_catalog_row_count": row_count,
            "exact_restore_pass_count_min": row_count,
            "exact_restore_pass_count_observed": exact_restore,
            "mean_saving_rate_observed": mean_saving,
            "mean_saving_rate_min_research": 0.0,
            "mask_token_exact_restore_required": True,
            "jaccard_axis": "separate_from_exact_restore",
        },
        "human_signoff": {"reviewer": None, "approved_at_utc": None, "note": None},
        "apply_command_after_signoff": None,
        "forbidden_in_this_envelope": [
            "automatic_active_swap",
            "customer_sla_claim",
            "en_business_headline_merge",
            "coding_deep_pack_headline_merge",
            "wtt_shortcap_only_headline_as_cs_mask_metric",
            "tier_a_operational_pass_as_cs_pack_metric",
        ],
        "reproduce": [
            "py scripts/build_compression_ko_premium_cs_deep_pack_gate_v1.py",
            "py scripts/build_compression_ko_premium_cs_deep_pack_signoff_envelope_v1.py",
            "py scripts/build_compression_ko_premium_cs_deep_pack_signoff_checklist_v1.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build ko premium cs deep pack signoff envelope")
    ap.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.gate.is_file():
        print(f"MISSING gate: {args.gate}", file=sys.stderr)
        return 1
    doc = build_envelope(gate_path=args.gate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(args.out), "row_count": doc["promotion_gates_at_apply"]["template_catalog_row_count"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
