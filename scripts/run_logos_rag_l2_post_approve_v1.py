#!/usr/bin/env python3
"""Post L2 approval: R6 ko_only lane → merge → Track_C_advisory bridge → ingest status."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports/constitution" / "btrack_pilot"
BRIDGE = ART / "semantic_rag_bridge_insight_bundle_v1_latest.json"
L2_APPROVAL = ART / "logos_rag_btrack_promotion_human_approval_v1_latest.json"
DEFAULT_OUT = ART / "logos_rag_l2_post_ingest_v1_latest.json"
MERGED_R6 = PILOT / "philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "step": label,
        "exit_code": proc.returncode,
        "stderr_tail": None if proc.returncode == 0 else (proc.stderr or proc.stdout or "")[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not L2_APPROVAL.is_file():
        print("Missing L2 approval artifact", file=sys.stderr)
        return 2
    approval = json.loads(L2_APPROVAL.read_text(encoding="utf-8-sig"))
    tier = str(approval.get("tier") or "")
    if tier not in ("L2", "L3"):
        print(f"Latest approval is tier={tier or None}, expected L2 or L3", file=sys.stderr)
        return 2

    py = sys.executable
    steps: list[dict[str, Any]] = []

    steps.append(
        _run(
            [py, str(ROOT / "scripts/run_logos_rag_r6_ko_only_lane_v1.py"), "--skip-signoff"],
            "r6_ko_only_lane",
        )
    )
    steps.append(
        _run(
            [
                py,
                str(ROOT / "scripts/merge_logos_rag_pilot_ko_v1.py"),
                "--glob",
                "philosophy_lane_rag_pilot_r6_*_ko_only_latest.json",
                "--out",
                str(MERGED_R6),
                "--version-tag",
                "1.2.0",
            ],
            "merge_r6_pilots",
        )
    )
    merged = MERGED_R6 if MERGED_R6.is_file() else PILOT / "philosophy_lane_rag_pilot_r4_merged_q01_q12_ko_latest.json"
    steps.append(
        _run(
            [
                py,
                str(ROOT / "scripts/build_semantic_rag_bridge_insight_bundle_v1.py"),
                "--philosophy-pilot-json",
                str(merged),
                "--calibration-kind",
                "none",
                "--track",
                "Track_C_advisory",
                "--gating",
                "NON_GATING",
                "--summary-line",
                "L2 post-approve: Track C shadow ingest (ko_only R6 pilots; non-gating).",
                "--out",
                str(BRIDGE),
                "--strict",
            ],
            "bridge_track_c_advisory",
        )
    )
    steps.append(
        _run(
            [
                py,
                "-m",
                "pytest",
                "tests/test_semantic_rag_bridge_insight_bundle_schema_v1.py",
                "tests/test_build_semantic_rag_bridge_insight_bundle_v1.py",
                "-q",
            ],
            "pytest_bridge",
        )
    )
    steps.append(
        _run([py, str(ROOT / "scripts/check_logos_rag_btrack_promotion_gate_v1.py")], "promotion_gate")
    )

    bridge_n = 0
    validation_ok = False
    if BRIDGE.is_file():
        bdoc = json.loads(BRIDGE.read_text(encoding="utf-8-sig"))
        bridge_n = len(bdoc.get("rag_evidence") or [])
        validation_ok = bool((bdoc.get("bridge_meta") or {}).get("validation_ok"))

    failed = [s for s in steps if s.get("exit_code", 0) != 0]
    doc = {
        "schema": "logos_rag_l2_post_ingest_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "l2_approval_ts": approval.get("ts_utc"),
        "approval_tier": tier,
        "ingest_status": "complete" if not failed and validation_ok else "partial",
        "bridge": {
            "path": str(BRIDGE.relative_to(ROOT)),
            "rag_evidence_n": bridge_n,
            "validation_ok": validation_ok,
            "policy_track": "Track_C_advisory",
            "policy_gating": "NON_GATING",
            "merged_pilot": str(merged.relative_to(ROOT)) if merged.is_file() else None,
        },
        "steps": steps,
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False,
            "a_track_live_trading": False,
            "l3_production_index": False,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": not failed,
                "ingest_status": doc["ingest_status"],
                "bridge_evidence": bridge_n,
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
