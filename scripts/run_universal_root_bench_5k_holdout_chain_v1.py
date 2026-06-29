#!/usr/bin/env python3
"""MKM-UR-Bench-5K: holdout dual-plane B0/B3 chain [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

SOURCE_5K = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_5000_v1.json"
HOLDOUT_FIXTURE = ROOT / "tests/fixtures/universal_root_bench_5k_holdout_v1.json"
AUDIT_OUT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_bench5k_holdout_v1_latest.json"
CROSSWALK_OUT = ROOT / "reports/universal_root_topology_crosswalk_bench5k_holdout_v1_latest.json"
PHASE1A_OUT = ROOT / "reports/universal_root_bench_5k_holdout_phase1a_v1_latest.json"
CHAIN_REPORT = ROOT / "reports/universal_root_bench_5k_holdout_chain_v1_latest.json"

BUILD_HOLDOUT = ROOT / "scripts/build_universal_root_bench_5k_holdout_fixture_v1.py"
GEN_5K = ROOT / "scripts/bench/generate_massive_universal_root_pairs_v1.py"
AUDIT = ROOT / "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py"
CROSSWALK = ROOT / "scripts/build_universal_root_topology_crosswalk_v1.py"
PHASE1A = ROOT / "scripts/build_universal_root_phase1a_baseline_compare_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _method_value(doc: dict[str, Any], method_id: str) -> float | None:
    for m in doc.get("methods") or []:
        if m.get("id") == method_id:
            val = m.get("primary_value")
            return float(val) if val is not None else None
    return None


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    tail = (proc.stdout or proc.stderr or "")[-500:]
    return proc.returncode, tail


def run_chain(
    *,
    ensure_5k: bool,
    target_5k: int,
    seed: int,
    min_holdout_pairs: int,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    if ensure_5k and not SOURCE_5K.is_file():
        code, tail = _run([PY, str(GEN_5K), "--target", str(target_5k), "--seed", str(seed)])
        steps.append({"step": "generate_5k", "exit_code": code, "tail": tail})
        if code != 0:
            return {"ok": False, "steps": steps, "error": "generate_5k_failed"}

    code, tail = _run(
        [
            PY,
            str(BUILD_HOLDOUT),
            "--source",
            str(SOURCE_5K),
            "--out",
            str(HOLDOUT_FIXTURE),
            "--min-pairs",
            str(min_holdout_pairs),
        ]
    )
    steps.append({"step": "build_holdout_fixture", "exit_code": code, "tail": tail})
    if code != 0:
        return {"ok": False, "steps": steps, "error": "holdout_fixture_failed"}

    code, tail = _run(
        [
            PY,
            str(AUDIT),
            "--fixture",
            str(HOLDOUT_FIXTURE),
            "--out",
            str(AUDIT_OUT),
        ]
    )
    steps.append({"step": "lexicon_audit", "exit_code": code, "tail": tail})
    if code != 0:
        return {"ok": False, "steps": steps, "error": "lexicon_audit_failed"}

    code, tail = _run(
        [
            PY,
            str(CROSSWALK),
            "--fixture",
            str(HOLDOUT_FIXTURE),
            "--lexicon-audit",
            str(AUDIT_OUT),
            "--out",
            str(CROSSWALK_OUT),
        ]
    )
    steps.append({"step": "topology_crosswalk", "exit_code": code, "tail": tail})
    if code != 0:
        return {"ok": False, "steps": steps, "error": "topology_crosswalk_failed"}

    code, tail = _run(
        [
            PY,
            str(PHASE1A),
            "--skip-crosswalk-build",
            "--crosswalk",
            str(CROSSWALK_OUT),
            "--lexicon-audit",
            str(AUDIT_OUT),
            "--out",
            str(PHASE1A_OUT),
        ]
    )
    steps.append({"step": "phase1a_b0_b3", "exit_code": code, "tail": tail})
    if code != 0:
        return {"ok": False, "steps": steps, "error": "phase1a_failed"}

    phase1a = _read(PHASE1A_OUT)
    audit = _read(AUDIT_OUT)
    crosswalk = _read(CROSSWALK_OUT)
    holdout = _read(HOLDOUT_FIXTURE)

    b0 = _method_value(phase1a, "B0")
    b3 = _method_value(phase1a, "B3")
    b1 = _method_value(phase1a, "B1")
    b2 = _method_value(phase1a, "B2")

    return {
        "ok": True,
        "steps": steps,
        "bench_name": "MKM-UR-Bench-5K",
        "holdout_pair_count": int(holdout.get("pair_count") or 0),
        "methods": {
            "B0_english_only_hit_rate": b0,
            "B1_lexicon_prime_hit_rate": b1,
            "B2_topology_reachable_rate": b2,
            "B3_dual_plane_aligned_rate": b3,
        },
        "delta_b3_minus_b0": round((b3 or 0) - (b0 or 0), 4) if b3 is not None and b0 is not None else None,
        "lexicon_plane": crosswalk.get("lexicon_plane"),
        "topology_plane": crosswalk.get("topology_plane"),
        "wall_divergence": crosswalk.get("wall_divergence"),
        "audit_prime_hit_rate": (audit.get("baseline") or {}).get("prime_hit_rate"),
        "artifacts": {
            "holdout_fixture": str(HOLDOUT_FIXTURE.relative_to(ROOT)).replace("\\", "/"),
            "audit": str(AUDIT_OUT.relative_to(ROOT)).replace("\\", "/"),
            "crosswalk": str(CROSSWALK_OUT.relative_to(ROOT)).replace("\\", "/"),
            "phase1a": str(PHASE1A_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ensure-5k", action="store_true", help="Regenerate 5K fixture if missing")
    ap.add_argument("--target-5k", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-holdout-pairs", type=int, default=500)
    ap.add_argument("--report", type=Path, default=CHAIN_REPORT)
    args = ap.parse_args()

    result = run_chain(
        ensure_5k=args.ensure_5k,
        target_5k=args.target_5k,
        seed=args.seed,
        min_holdout_pairs=args.min_holdout_pairs,
    )

    doc = {
        "schema": "universal_root_bench_5k_holdout_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        **result,
        "reproduce": "py scripts/run_universal_root_bench_5k_holdout_chain_v1.py",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": result.get("ok"),
                "holdout_pair_count": result.get("holdout_pair_count"),
                "B0": (result.get("methods") or {}).get("B0_english_only_hit_rate"),
                "B3": (result.get("methods") or {}).get("B3_dual_plane_aligned_rate"),
                "delta_b3_minus_b0": result.get("delta_b3_minus_b0"),
                "report": str(args.report),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
