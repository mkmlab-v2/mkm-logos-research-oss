#!/usr/bin/env python3
"""[HYPO] Next NG-40 progress: dual-axis cap grid, DE handoff, sign-off packet, BLS, auto_ops."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/ng40_next_progress_chain_v1_latest.json"
PROBE = ROOT / "reports/bls_unemployment_probe_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:400]}
    return {"script": script, "args": extra or [], "exit_code": int(cp.returncode), "parsed": parsed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-dual-axis-push", action="store_true", help="Skip 320-combo grid")
    ap.add_argument("--skip-auto-ops", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc = 0

    if not args.skip_dual_axis_push:
        s = _run_py(
            "scripts/run_ng40_path_b_dual_axis_push_v1.py",
            ["--skip-promotion-packet"],
        )
        steps.append({"name": "path_b_dual_axis_push", **s})
        if s["exit_code"] != 0:
            rc = s["exit_code"]

    steps.append(
        _run_py(
            "scripts/run_ng40_genai_de_research_handoff_v1.py",
            ["--run-local-refresh"],
        )
    )

    s_pkt = _run_py(
        "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py",
        [
            "--path-b-knee-research-signoff",
            "--path-a-product-research-signoff",
            "--reviewer",
            "commander",
            "--note",
            "next_progress trilane knee + path_a product 2026-06-04",
        ],
    )
    steps.append({"name": "promotion_packet", **s_pkt})

    s_bls = _run_py("scripts/probe_bls_unemployment_may2026_v1.py")
    steps.append({"name": "bls_probe", **s_bls})
    bls_resolved = False
    if PROBE.is_file():
        doc = json.loads(PROBE.read_text(encoding="utf-8-sig"))
        if doc.get("may_2026_release_ready") and doc.get("suggested_outcome"):
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ROOT / "scripts/Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1"),
                    "-Outcome",
                    str(doc["suggested_outcome"]),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            steps.append(
                {
                    "name": "bls_resolve",
                    "exit_code": int(proc.returncode),
                }
            )
            bls_resolved = proc.returncode == 0

    if not args.skip_auto_ops:
        steps.append(
            _run_py(
                "scripts/run_ng40_recommended_auto_ops_v1.py",
                ["--skip-tri-lane-execute"],
            )
        )

    push = {}
    push_path = ROOT / "reports/ng40_path_b_dual_axis_push_v1_latest.json"
    if push_path.is_file():
        push = json.loads(push_path.read_text(encoding="utf-8-sig"))

    promo = {}
    pkt = ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
    if pkt.is_file():
        promo = json.loads(pkt.read_text(encoding="utf-8-sig"))

    manifest = {
        "schema": "ng40_next_progress_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "steps": steps,
        "dual_axis_push": {
            "any_beat_frozen": push.get("any_beat_frozen_vs_active"),
            "combo_count": push.get("combo_count"),
        },
        "export_prep_ready": (s_pkt.get("parsed") or {}).get("export_prep_ready")
        if isinstance(s_pkt.get("parsed"), dict)
        else promo.get("export_prep_ready"),
        "selected_arm": promo.get("selected_arm"),
        "apply_forbidden": promo.get("apply_forbidden"),
        "bls_resolved": bls_resolved,
        "forbidden": ["--apply-active"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "rc": rc,
                "export_prep_ready": manifest["export_prep_ready"],
                "selected_arm": manifest["selected_arm"],
                "any_beat": push.get("any_beat_frozen_vs_active"),
            },
            ensure_ascii=False,
        )
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
