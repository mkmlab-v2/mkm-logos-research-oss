#!/usr/bin/env python3
"""Build commander human-review checklist for en business deep pack signoff."""

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

DEFAULT_GATE = ROOT / "docs/final/artifacts/compression_en_business_deep_pack_gate_v1_latest.json"
DEFAULT_ENVELOPE = ROOT / "docs/final/artifacts/compression_en_business_deep_pack_promotion_signoff_envelope_v1_latest.json"
DEFAULT_FALLBACK = ROOT / "docs/final/artifacts/compression_en_business_deep_pack_fallback_spec_v1_latest.json"
DEFAULT_SPEC = ROOT / "docs/final/artifacts/compression_en_business_deep_pack_spec_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_en_business_deep_pack_signoff_checklist_v1_latest.json"
TEMPLATE_MANIFEST = ROOT / "codebook/templates/zone_h_en_business_templates_manifest_v1.json"
CODING_GATE = ROOT / "docs/final/artifacts/compression_coding_deep_pack_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_checklist(
    *,
    gate_path: Path,
    envelope_path: Path,
    fallback_path: Path,
    spec_path: Path,
) -> dict[str, Any]:
    gate = _load(gate_path)
    envelope = _load(envelope_path)
    fallback = _load(fallback_path)
    spec = _load(spec_path) if spec_path.is_file() else {}

    summary = gate.get("summary") or {}
    catalog = gate.get("template_catalog") or {}
    row_count = int(catalog.get("row_count") or summary.get("case_count") or 0)
    exact_restore = int(summary.get("exact_restore_pass_count") or 0)
    roundtrip_path = str(gate.get("roundtrip_path") or "")
    promo = envelope.get("promotion_gates_at_apply") or {}

    checklist = {
        "twin_gate_exact_restore_all_pass": exact_restore >= row_count > 0,
        "wire_family_biz_mask": str(gate.get("wire_family") or "") == "BIZ_MASK",
        "roundtrip_path_template_catalog_wire_v1": roundtrip_path == "template_catalog_wire_v1",
        "research_only_true": bool(gate.get("research_only")) and bool(envelope.get("research_only")),
        "track_a_active_untouched_true": bool(gate.get("track_a_active_untouched"))
        and bool(envelope.get("track_a_active_untouched")),
        "send_gate_hold": str(gate.get("send_gate") or "").upper() == "HOLD"
        and str(envelope.get("send_gate") or "").upper() == "HOLD",
        "envelope_awaiting_commander": str(envelope.get("envelope_status") or "")
        == "draft_awaiting_commander",
        "fallback_spec_present": fallback_path.is_file()
        and fallback.get("schema") == "compression_en_business_deep_pack_fallback_spec_v1",
        "vertical_spec_present": spec_path.is_file()
        and spec.get("schema") == "compression_en_business_deep_pack_spec_v1",
        "template_manifest_present": TEMPLATE_MANIFEST.is_file(),
        "separate_from_coding_pack_ack": CODING_GATE.is_file(),
        "jaccard_axis_separate_ack": str((gate.get("twin_metrics_axis") or {}).get("secondary_axis"))
        == "jaccard_proxy",
        "human_signoff_not_applied": not bool((envelope.get("human_signoff") or {}).get("reviewer")),
    }
    failed = [k for k, v in checklist.items() if not v]
    all_green = len(failed) == 0
    decision = "READY_FOR_COMMANDER_SIGNOFF" if all_green else "HOLD_NEEDS_REVIEW"

    return {
        "schema": "compression_en_business_deep_pack_signoff_checklist_v1",
        "generated_at_utc": _utc(),
        "decision": decision,
        "all_green": all_green,
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "vertical_id": "zone_h_en_business_v1",
        "wire_family": "BIZ_MASK",
        "checklist": checklist,
        "failed_checks": failed,
        "summary": {
            "template_catalog_row_count": row_count,
            "exact_restore_pass_count": exact_restore,
            "mean_saving_rate_observed": float(
                summary.get("mean_saving_rate") or promo.get("mean_saving_rate_observed") or 0.0
            ),
            "catalog_sha256": catalog.get("catalog_sha256"),
            "envelope_status": envelope.get("envelope_status"),
        },
        "constraints": {
            "human_review_required": True,
            "automatic_active_swap": False,
            "b_to_a_auto_bridge": False,
        },
        "commander_review_items": [
            "Twin gate: saving_rate + exact_restore_ok together (not Jaccard alone).",
            "BIZ_MASK wire only — do not merge ZF_MASK coding pack or wtt CS shortcap headlines.",
            "English business formal axis — not Korean premium CS masked turns.",
            "SKU-COORD remains pointer/meta only — no customer SDK claims.",
            "Signoff approves research envelope only; ACTIVE swap requires separate Track A gate.",
        ],
        "evidence_paths": {
            "gate_artifact": _rel(gate_path),
            "signoff_envelope": _rel(envelope_path),
            "fallback_spec": _rel(fallback_path),
            "vertical_spec": _rel(spec_path),
            "template_manifest": _rel(TEMPLATE_MANIFEST),
            "coding_pack_gate_separation": _rel(CODING_GATE),
        },
        "operator_action": {
            "approve_if_all_green": all_green,
            "review_items_if_hold": failed,
            "after_commander_signoff": [
                "Set human_signoff.reviewer + approved_at_utc on signoff envelope (manual edit).",
                "Do NOT run ACTIVE apply without explicit Track A promotion order.",
            ],
        },
        "reproduce": [
            "py scripts/build_compression_en_business_deep_pack_gate_v1.py",
            "py scripts/build_compression_en_business_deep_pack_signoff_envelope_v1.py",
            "py scripts/build_compression_en_business_deep_pack_signoff_checklist_v1.py",
            "py -m pytest tests/test_compression_en_business_deep_pack_v1.py tests/test_build_compression_en_business_deep_pack_signoff_checklist_v1.py -q",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build en business deep pack commander signoff checklist")
    ap.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--envelope", type=Path, default=DEFAULT_ENVELOPE)
    ap.add_argument("--fallback", type=Path, default=DEFAULT_FALLBACK)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    for label, p in (("gate", args.gate), ("envelope", args.envelope), ("fallback", args.fallback)):
        if not p.is_file():
            print(f"MISSING {label}: {p}", file=sys.stderr)
            return 1
    doc = build_checklist(
        gate_path=args.gate,
        envelope_path=args.envelope,
        fallback_path=args.fallback,
        spec_path=args.spec,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "decision": doc["decision"], "all_green": doc["all_green"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
