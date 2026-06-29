#!/usr/bin/env python3
"""HD delegation chain: sasang routing sidecar build + narrative A/B + sweep ([HYPO])."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/sasang_routing_sidecar_hd_delegation_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-router", action="store_true", help="fast structural smoke only")
    ap.add_argument("--skip-full-panel", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    chain = [
        ([sys.executable, str(ROOT / "scripts/run_sasang_routing_sidecar_on_gematria_path_chain_v1.py")], "sidecar_chain"),
        ([sys.executable, str(ROOT / "scripts/run_sasang_routing_sidecar_narrative_path_ab_chain_v1.py")] + (["--skip-router"] if args.skip_router else []), "ab_fixed_8"),
        ([sys.executable, str(ROOT / "scripts/run_sasang_routing_sidecar_narrative_ab_sweep_v1.py"), "--panel", "fixed"] + (["--skip-router"] if args.skip_router else []), "sweep_fixed_profiles"),
    ]
    if not args.skip_full_panel:
        chain.append(
            (
                [
                    sys.executable,
                    str(ROOT / "scripts/bench_sasang_routing_sidecar_narrative_path_ab_v1.py"),
                    "--panel",
                    "full",
                    "--profile",
                    "observe",
                    "--tag",
                    "full_observe",
                ]
                + (["--skip-router"] if args.skip_router else []),
                "ab_full_200_observe",
            )
        )
        chain.append(
            (
                [
                    sys.executable,
                    str(ROOT / "scripts/check_sasang_routing_sidecar_narrative_path_ab_v1.py"),
                    "--in",
                    str(ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_full_observe_latest.json"),
                    "--out",
                    str(ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_gate_full_observe_latest.json"),
                    "--min-sidecar-pass-rate",
                    "0.90",
                ],
                "gate_full_200_observe",
            )
        )

    for cmd, step_id in chain:
        code = _run(cmd)
        steps.append({"id": step_id, "exit_code": code, "ok": code == 0})
        if code != 0:
            break

    ok = all(s["ok"] for s in steps)
    report = {
        "schema": "sasang_routing_sidecar_hd_delegation_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "steps": steps,
        "reproduce": "py scripts/run_sasang_routing_sidecar_hd_delegation_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "steps": len(steps), "out": str(args.out)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
