#!/usr/bin/env python3
"""[HYPO] RQ-024 nf5 blocked-WF v2 vs v1 re-check — rerun smoke + stability cross-read."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SMOKE = ROOT / "reports/rq024_btc_lens_v2_nf5_wf_smoke_v1_latest.json"
DEFAULT_STABILITY = ROOT / "reports/rq024_btc_lens_v1_wf_stability_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq024_nf5_wf_v2_vs_v1_recheck_v1_latest.json"
SCHEMA = "rq024_nf5_wf_v2_vs_v1_recheck_v1"
SMOKE_SCRIPT = ROOT / "scripts/run_rq024_btc_lens_v2_nf5_wf_smoke_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rerun-smoke", action="store_true", help="Re-execute nf5 smoke before compare")
    ap.add_argument("--smoke-json", type=Path, default=DEFAULT_SMOKE)
    ap.add_argument("--stability-json", type=Path, default=DEFAULT_STABILITY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    smoke_path = args.smoke_json if args.smoke_json.is_absolute() else ROOT / args.smoke_json
    stab_path = args.stability_json if args.stability_json.is_absolute() else ROOT / args.stability_json
    out_path = args.output if args.output.is_absolute() else ROOT / args.output

    if args.rerun_smoke:
        proc = subprocess.run(
            [sys.executable, str(SMOKE_SCRIPT), "--output", str(smoke_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            raise SystemExit(f"smoke failed: {proc.stderr}")

    if not smoke_path.is_file():
        raise SystemExit(f"missing smoke: {smoke_path}")

    smoke = _load(smoke_path)
    stab = _load(stab_path) if stab_path.is_file() else {}

    v1_mean = float((smoke.get("v1_aggregate") or {}).get("mean_test_accuracy") or 0)
    v2_mean = float((smoke.get("v2_aggregate") or {}).get("mean_test_accuracy") or 0)
    delta = round(v2_mean - v1_mean, 6)

    nf5_stab = None
    for row in stab.get("nf_sensitivity") or []:
        if row.get("slug") == "nf5_margin_vs_bull_srcdir_rq024_v0_v1":
            nf5_stab = row
            break

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "smoke_pointer": str(smoke_path.relative_to(ROOT)).replace("\\", "/"),
        "stability_pointer": str(stab_path.relative_to(ROOT)).replace("\\", "/") if stab_path.is_file() else None,
        "nf5": {
            "v1_mean_test_accuracy": v1_mean,
            "v2_mean_test_accuracy": v2_mean,
            "delta_v2_minus_v1": delta,
            "v1_gate_055_pass": v1_mean >= 0.55,
            "v2_gate_055_pass": v2_mean >= 0.55,
            "v1_beats_ceiling_052": v1_mean > 0.52,
            "v2_beats_ceiling_052": v2_mean > 0.52,
        },
        "stability_nf5_crosscheck": nf5_stab,
        "verdict": {
            "v2_improves_over_v1": delta > 0,
            "track_a_promotion": False,
            "note": "research_only — gate 0.55 fail unless mean>=0.55",
        },
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} v1={v1_mean} v2={v2_mean} delta={delta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
