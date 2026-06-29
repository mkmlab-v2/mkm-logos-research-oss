#!/usr/bin/env python3
"""Entropy-leg profile sweep for sasang routing sidecar narrative A/B ([HYPO])."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_sweep_v1_latest.json"
PROFILES = ("observe", "tactical", "structural")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel", choices=("fixed", "full"), default="fixed")
    ap.add_argument("--skip-router", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    bench = ROOT / "scripts/bench_sasang_routing_sidecar_narrative_path_ab_v1.py"
    gate = ROOT / "scripts/check_sasang_routing_sidecar_narrative_path_ab_v1.py"
    min_rate = 0.875 if args.panel == "fixed" else 0.90

    rows: list[dict] = []
    for profile in PROFILES:
        tag = f"{args.panel}_{profile}"
        report_path = ROOT / f"reports/sasang_routing_sidecar_narrative_path_ab_{tag}_latest.json"
        gate_path = ROOT / f"reports/sasang_routing_sidecar_narrative_path_ab_gate_{tag}_latest.json"
        cmd = [
            sys.executable,
            str(bench),
            "--panel",
            args.panel,
            "--profile",
            profile,
            "--tag",
            tag,
            "--out",
            str(report_path),
        ]
        if args.skip_router:
            cmd.append("--skip-router")
        code = _run(cmd)
        if code != 0:
            return code

        gate_cmd = [
            sys.executable,
            str(gate),
            "--in",
            str(report_path),
            "--out",
            str(gate_path),
            "--min-sidecar-pass-rate",
            str(min_rate),
        ]
        gate_code = _run(gate_cmd)
        doc = json.loads(report_path.read_text(encoding="utf-8-sig"))
        gate_doc = json.loads(gate_path.read_text(encoding="utf-8-sig")) if gate_path.is_file() else {}
        rows.append(
            {
                "profile": profile,
                "report": str(report_path.relative_to(ROOT)).replace("\\", "/"),
                "gate": str(gate_path.relative_to(ROOT)).replace("\\", "/"),
                "panel_n": doc.get("panel_sample_count"),
                "sidecar_gate_pass_rate": (doc.get("arm_on") or {}).get("sidecar_gate_pass_rate"),
                "mean_router_paths_delta": (doc.get("delta") or {}).get("narrowed_router_paths_minus_baseline"),
                "gate_ok": gate_doc.get("ok"),
            }
        )
        if gate_code != 0:
            print(json.dumps({"ok": False, "failed_profile": profile}))
            return gate_code

    sweep = {
        "schema": "sasang_routing_sidecar_narrative_path_ab_sweep_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "panel": args.panel,
        "profiles": list(PROFILES),
        "rows": rows,
        "reproduce": "py scripts/run_sasang_routing_sidecar_narrative_ab_sweep_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(sweep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "profiles": len(rows), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
