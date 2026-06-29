#!/usr/bin/env python3
"""[HYPO] NG-40 ordered ops: hybrid eval → structure → BLS → codec split → Path A → promotion."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/ng40_ordered_full_chain_v1_latest.json"
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
    return {
        "order_step": script,
        "args": extra or [],
        "exit_code": int(cp.returncode),
        "parsed": parsed,
    }


def _run_ps1(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ROOT / "scripts" / script),
        *(extra or []),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "order_step": script,
        "args": extra or [],
        "exit_code": int(cp.returncode),
        "stderr_tail": (cp.stderr or "")[-300:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-structure", action="store_true")
    ap.add_argument("--skip-auto-ops", action="store_true")
    ap.add_argument("--run-path-b-sweep", action="store_true", help="Slow 320-combo in codec split")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc_final = 0

    # 1) Latent + spine hybrid rollup
    s1 = _run_py("scripts/run_ng40_latent_spine_hybrid_eval_chain_v1.py")
    steps.append({"step": 1, "name": "latent_spine_hybrid_eval", **s1})
    if s1["exit_code"] != 0:
        rc_final = s1["exit_code"]

    # 2) Path B structure (+ coordinator)
    if not args.skip_structure and rc_final == 0:
        s2 = _run_py(
            "scripts/run_ng40_path_b_structure_experiment_chain_v1.py",
            ["--skip-diet"],
        )
        steps.append({"step": 2, "name": "path_b_structure_experiment", **s2})
        if s2["exit_code"] != 0:
            rc_final = s2["exit_code"]

    # 3) BLS probe → resolve only when ready
    s3 = _run_py("scripts/probe_bls_unemployment_may2026_v1.py")
    steps.append({"step": 3, "name": "bls_probe", **s3})
    bls_resolved = False
    if PROBE.is_file():
        probe_doc = json.loads(PROBE.read_text(encoding="utf-8-sig"))
        if probe_doc.get("may_2026_release_ready") and probe_doc.get("suggested_outcome"):
            outcome = probe_doc["suggested_outcome"]
            s3b = _run_ps1(
                "Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1",
                ["-Outcome", outcome],
            )
            steps.append({"step": 3, "name": "bls_resolve", **s3b})
            bls_resolved = s3b["exit_code"] == 0
        else:
            steps.append(
                {
                    "step": 3,
                    "name": "bls_resolve",
                    "skipped": True,
                    "reason": probe_doc.get("status"),
                }
            )

    # 4–5) Codec split → Path A product
    if rc_final == 0:
        extra4 = [] if args.run_path_b_sweep else ["--skip-path-b-sweep"]
        s4 = _run_py("scripts/run_ng40_codec_bench_split_chain_v1.py", extra4)
        steps.append({"step": 4, "name": "codec_bench_split", **s4})
        if s4["exit_code"] != 0:
            rc_final = s4["exit_code"]
        else:
            extra5 = ["--skip-auto-ops"]
            s5 = _run_py("scripts/run_ng40_path_a_product_signoff_chain_v1.py", extra5)
            steps.append({"step": 5, "name": "path_a_product_signoff", **s5})
            if s5["exit_code"] != 0:
                rc_final = s5["exit_code"]

    # 6) Promotion packet (research sign-offs)
    s6 = _run_py(
        "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py",
        [
            "--path-b-knee-research-signoff",
            "--path-a-product-research-signoff",
            "--reviewer",
            "commander",
            "--note",
            "ng40_ordered_full_chain 2026-06-04",
        ],
    )
    steps.append({"step": 6, "name": "promotion_packet", **s6})

    # 7) Recommended auto ops (patrol, merge, handoff)
    if not args.skip_auto_ops:
        s7 = _run_py(
            "scripts/run_ng40_recommended_auto_ops_v1.py",
            ["--skip-tri-lane-execute"],
        )
        steps.append({"step": 7, "name": "recommended_auto_ops", **s7})
        if s7["exit_code"] != 0 and rc_final == 0:
            rc_final = s7["exit_code"]

    packet = {}
    pkt_path = ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
    if pkt_path.is_file():
        packet = json.loads(pkt_path.read_text(encoding="utf-8-sig"))

    promo_step = next((s for s in steps if s.get("name") == "promotion_packet"), None)
    promo_parsed = (promo_step or {}).get("parsed") or {}
    export_prep = promo_parsed.get("export_prep_ready")
    if export_prep is None:
        export_prep = packet.get("export_prep_ready")
    apply_forbidden = promo_parsed.get("apply_forbidden")
    if apply_forbidden is None:
        apply_forbidden = packet.get("apply_forbidden")

    doc = {
        "schema": "ng40_ordered_full_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "steps": steps,
        "bls_resolved": bls_resolved,
        "export_prep_ready": export_prep,
        "apply_forbidden": apply_forbidden,
        "note_ko": "auto_ops가 패킷 덮어쓸 수 있음 — step6 promotion parsed 우선",
        "pointers": {
            "hybrid_eval": "reports/ng40_latent_spine_hybrid_eval_v1_latest.json",
            "structure": "reports/ng40_path_b_structure_experiment_v1_latest.json",
            "codec_split": (
                "experiments/nextgen_clean_slate_cpu_v1/results/"
                "ng40_codec_bench_split_manifest_v1_latest.json"
            ),
            "path_a_signoff": "reports/ng40_path_a_product_signoff_chain_v1_latest.json",
            "promotion": "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json",
        },
        "forbidden": ["--apply-active"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "rc_final": rc_final,
                "export_prep_ready": doc["export_prep_ready"],
                "bls_resolved": bls_resolved,
            },
            ensure_ascii=False,
        )
    )
    return rc_final


if __name__ == "__main__":
    raise SystemExit(main())
