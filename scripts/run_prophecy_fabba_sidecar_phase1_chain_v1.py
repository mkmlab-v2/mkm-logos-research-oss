#!/usr/bin/env python3
"""[HYPO] Phase 1+ chain: dual-leg 2bps WF + param sweep + feature_lut + bridge manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/prophecy_fabba_sidecar_phase1_chain_v1_latest.json"
DUAL_LEG = ROOT / "scripts/run_prophecy_fabba_sidecar_dual_leg_wf_v1.py"
SWEEP = ROOT / "scripts/run_prophecy_fabba_sidecar_param_sweep_v1.py"
LUT_BUILD = ROOT / "scripts/build_prophecy_fabba_sidecar_feature_lut_v1.py"
BTRACK_LUT = ROOT / "reports/btrack_ohlcv_feature_lut_v1_latest.json"
SCHEMA = "prophecy_fabba_sidecar_phase1_chain_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (p.stdout or "") + (p.stderr or "")
    return int(p.returncode), tail.strip()[-500:]


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-sweep", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    py = sys.executable

    dual_out = ROOT / "reports/prophecy_fabba_sidecar_dual_leg_wf_v1_latest.json"
    rc, tail = _run([py, str(DUAL_LEG), "--output", str(dual_out)])
    steps.append({"step": "dual_leg_wf", "exit_code": rc, "artifact": str(dual_out.relative_to(ROOT)), "tail": tail})
    if rc != 0:
        return _fail(args.output, steps, rc)

    sweep_out = ROOT / "reports/prophecy_fabba_sidecar_param_sweep_v1_latest.json"
    if not args.skip_sweep:
        rc, tail = _run([py, str(SWEEP), "--output", str(sweep_out), "--backend", "apca_stub"])
        steps.append({"step": "param_sweep", "exit_code": rc, "artifact": str(sweep_out.relative_to(ROOT)), "tail": tail})
        if rc != 0:
            return _fail(args.output, steps, rc)
    else:
        steps.append({"step": "param_sweep", "skipped": True})

    lut_out = ROOT / "reports/prophecy_fabba_sidecar_feature_lut_v1_latest.json"
    rc, tail = _run(
        [
            py,
            str(LUT_BUILD),
            "--include-btc",
            "--eval-days",
            "180",
            "--neutral-bps",
            "2.0",
            "--output",
            str(lut_out),
            "--backend",
            "apca_stub",
        ]
    )
    steps.append({"step": "feature_lut_export", "exit_code": rc, "artifact": str(lut_out.relative_to(ROOT)), "tail": tail})
    if rc != 0:
        return _fail(args.output, steps, rc)

    bridge_out = ROOT / "reports/prophecy_fabba_sidecar_btrack_bridge_v1_latest.json"
    dual_doc = _load(dual_out) or {}
    sweep_doc = _load(sweep_out) if not args.skip_sweep else None
    best = (sweep_doc or {}).get("best_by_ngram_pooled_hr") or {}
    bridge = {
        "schema": "prophecy_fabba_sidecar_btrack_bridge_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "pointers": {
            "btrack_ohlcv_feature_lut": str(BTRACK_LUT.relative_to(ROOT)).replace("\\", "/")
            if BTRACK_LUT.is_file()
            else None,
            "fabba_sidecar_feature_lut": str(lut_out.relative_to(ROOT)).replace("\\", "/"),
            "dual_leg_wf_shadow": str(dual_out.relative_to(ROOT)).replace("\\", "/"),
            "param_sweep": str(sweep_out.relative_to(ROOT)).replace("\\", "/") if sweep_doc else None,
        },
        "recommended_shadow_params_from_sweep": best,
        "usage_ko": "Primary WF/score는 btrack_ohlcv_feature_lut; fabba_* 컬럼은 sidecar meta만 — merge는 read-only join.",
    }
    bridge_out.write_text(json.dumps(bridge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    steps.append({"step": "bridge_manifest", "exit_code": 0, "artifact": str(bridge_out.relative_to(ROOT))})

    cmp_block = dual_doc.get("compare_primary_recommended_chain") or {}
    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_mutated": False,
        "steps": steps,
        "dual_leg_summary": cmp_block,
        "sweep_best": best,
        "bridge_pointer": str(bridge_out.relative_to(ROOT)).replace("\\", "/"),
        "verdict_ko": [
            "sidecar ngram dual-leg pooled vs Primary 45% — shadow only, no Track A merge",
            "param sweep best row = research default tol/ngram; re-validate on dual-leg before any feature_lut consumer",
        ],
        "reproduce": "py scripts/run_prophecy_fabba_sidecar_phase1_chain_v1.py",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} "
        f"ngram_vs_primary_pp={cmp_block.get('sidecar_ngram_vs_primary_pp')} "
        f"best_tol={best.get('tol')}"
    )
    return 0


def _fail(out_path: Path, steps: list[dict[str, Any]], rc: int) -> int:
    doc = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "status": "failed",
        "steps": steps,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
