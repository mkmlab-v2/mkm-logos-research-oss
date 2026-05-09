#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
ORCH = ROOT / "scripts" / "mkm_global_orchestrator_v1.py"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Sensitivity sweep for GO cuts without target-board dependency.")
    ap.add_argument("--sasang-json", type=Path, default=ART / "sasang_independent_lens_latest.json")
    ap.add_argument("--myeongni-json", type=Path, default=ART / "mkm_myeongni_response_v2_latest.json")
    ap.add_argument("--logos-json", type=Path, default=ART / "mkm_logos_response_v2_latest.json")
    ap.add_argument("--runtime-json", type=Path, default=ROOT / "reports" / "myeongni_conflict_arbitration_runtime_mode_latest.json")
    ap.add_argument("--realset-gate-json", type=Path, default=ART / "myeongni_stage2_realset_gate_latest.json")
    ap.add_argument("--output-json", type=Path, default=ART / "mkm_orchestrator_policy_sensitivity_latest.json")
    args = ap.parse_args()

    go_conf_cuts = [0.50, 0.53, 0.56, 0.60]
    go_dir_cuts = [0.12, 0.14, 0.16, 0.18]
    rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="mkm_sweep_") as td:
        tdp = Path(td)
        for ccut in go_conf_cuts:
            for dcut in go_dir_cuts:
                policy = {
                    "schema": "mkm_global_orchestrator_policy_v1",
                    "weights": {"sasang": 0.34, "myeongni": 0.33, "logos": 0.33},
                    "decision_policy": {
                        "go_confidence_cut": ccut,
                        "go_direction_abs_cut": dcut,
                        "hold_confidence_cut": 0.35,
                        "hold_direction_abs_cut": 0.10,
                        "fail_closed_action": "HOLD",
                    },
                }
                p_path = tdp / f"policy_{ccut}_{dcut}.json"
                o_path = tdp / f"out_{ccut}_{dcut}.json"
                p_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

                cp = subprocess.run(
                    [
                        sys.executable,
                        str(ORCH),
                        "--sasang-json",
                        str(args.sasang_json),
                        "--myeongni-json",
                        str(args.myeongni_json),
                        "--logos-json",
                        str(args.logos_json),
                        "--policy-json",
                        str(p_path),
                        "--myeongni-runtime-json",
                        str(args.runtime_json),
                        "--myeongni-realset-gate-json",
                        str(args.realset_gate_json),
                        "--output-json",
                        str(o_path),
                    ],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                )
                decision = "ERROR"
                dscore = 0.0
                conf = 0.0
                if cp.returncode in {0, 2} and o_path.is_file():
                    out = _read_json(o_path)
                    r = out.get("result") if isinstance(out.get("result"), dict) else {}
                    decision = str(r.get("decision") or "ERROR")
                    dscore = float(r.get("final_direction_score") or 0.0)
                    conf = float(r.get("final_confidence") or 0.0)

                rows.append(
                    {
                        "go_confidence_cut": ccut,
                        "go_direction_abs_cut": dcut,
                        "decision": decision,
                        "final_direction_score": dscore,
                        "final_confidence": conf,
                    }
                )

    go_rows = [r for r in rows if r["decision"] == "GO"]
    report = {
        "schema": "mkm_orchestrator_policy_sensitivity_v1",
        "generated_at_utc": _now(),
        "grid_size": len(rows),
        "go_count": len(go_rows),
        "rows": rows,
        "recommendation": {
            "note": "Prefer highest conservative cuts that still keep GO under current non-board conditions.",
            "candidate_rows": go_rows[:5],
        },
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "grid_size": len(rows), "go_count": len(go_rows), "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
