#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.55, K:0.8, M:0.35}
# Balance: 85
# Purpose: Paired V2 evaluate_report artifacts for bridge policy OFF vs ON (same caps).
# Keywords: multilens, gematria, bridge_policy, snapshot
"""Emit paired artifacts: apply_gematria_4d_bridge_policy False vs True at fixed AB-class caps.

Does not change engine defaults. Use for explicit \"Premium / bridge ON\" profile documentation
and diff against MULTILENS_BRIDGE_POLICY_AB_* historical files.
"""

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

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
OUT_OFF = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_OFF_V1.json"
OUT_ON = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_ON_V1.json"
OUT_MANIFEST = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_MANIFEST_V1.json"

# Same caps as MULTILENS_BRIDGE_POLICY_AB_OFF_V1 / ON_V1 (Fact-Lock: compare only within this class).
_STRATEGY = "A"
_INTENSITY = "extreme"
_GENERAL_CAP = 0.54
_SENSITIVE_CAP = 0.5
_HANGUL_CAP = 0.48
_MUST_KEEP = frozenset({"사상의학", "체질", "sasang", "myeongri", "bible"})


def _build_report(*, apply_gematria_4d_bridge_policy: bool) -> dict[str, Any]:
    doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    baseline_j = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    report = evaluate_report(
        doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=_STRATEGY,
        intensity=_INTENSITY,
        must_keep=set(_MUST_KEEP),
        jaccard_drop_threshold_pp=2.0,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=_GENERAL_CAP,
        sensitive_max_saving_rate=_SENSITIVE_CAP,
        hangul_max_saving_rate=_HANGUL_CAP,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
        apply_gematria_4d_bridge_policy=apply_gematria_4d_bridge_policy,
    )
    report["snapshot_meta"] = {
        "schema": "multilens_v2_bridge_policy_snapshot_meta_v1",
        "bridge_policy": "on" if apply_gematria_4d_bridge_policy else "off",
        "caps_class": "multilens_bridge_policy_ab_class_v1",
        "fixed_caps": {
            "strategy": _STRATEGY,
            "intensity": _INTENSITY,
            "general_max_saving_rate": _GENERAL_CAP,
            "sensitive_max_saving_rate": _SENSITIVE_CAP,
            "hangul_max_saving_rate": _HANGUL_CAP,
        },
        "script": "scripts/run_multilens_v2_bridge_policy_snapshot.py",
        "note": "Separate artifact for explicit OFF/ON; does not change defaults elsewhere.",
    }
    return report


def _metrics_slice(rep: dict[str, Any]) -> dict[str, Any]:
    cm = rep.get("compression_metrics") or {}
    return {
        "avg_reconstruction_fidelity_jaccard": float(cm.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "global_token_saving_rate": float(cm.get("global_token_saving_rate", 0.0)),
        "avg_sensitive_integrity": float(cm.get("avg_sensitive_integrity", 0.0)),
        "case_count": int(cm.get("case_count", 0)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Write paired V2 bridge policy OFF/ON snapshot JSONs.")
    ap.add_argument(
        "--which",
        choices=("both", "off", "on"),
        default="both",
        help="Which snapshot(s) to write.",
    )
    ap.add_argument(
        "--manifest",
        action="store_true",
        help="Also write MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_MANIFEST_V1.json (default when --which both).",
    )
    args = ap.parse_args()
    write_manifest = bool(args.manifest) or args.which == "both"

    ts = datetime.now(timezone.utc).isoformat()
    off_rep: dict[str, Any] | None = None
    on_rep: dict[str, Any] | None = None

    if args.which in ("both", "off"):
        off_rep = _build_report(apply_gematria_4d_bridge_policy=False)
        OUT_OFF.parent.mkdir(parents=True, exist_ok=True)
        OUT_OFF.write_text(json.dumps(off_rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {OUT_OFF}", flush=True)
    if args.which in ("both", "on"):
        on_rep = _build_report(apply_gematria_4d_bridge_policy=True)
        OUT_ON.parent.mkdir(parents=True, exist_ok=True)
        OUT_ON.write_text(json.dumps(on_rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {OUT_ON}", flush=True)

    if write_manifest and off_rep is not None and on_rep is not None:
        manifest = {
            "schema": "multilens_v2_bridge_policy_snapshot_manifest_v1",
            "generated_at_utc": ts,
            "source_input": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
            "baseline_report": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json",
            "artifacts": {
                "off": "docs/final/artifacts/MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_OFF_V1.json",
                "on": "docs/final/artifacts/MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_ON_V1.json",
            },
            "metrics": {
                "off": _metrics_slice(off_rep),
                "on": _metrics_slice(on_rep),
            },
            "runner": "scripts/run_multilens_v2_bridge_policy_snapshot.py",
        }
        OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {OUT_MANIFEST}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
