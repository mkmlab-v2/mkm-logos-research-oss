#!/usr/bin/env python3
"""RQ-024 post-triangle chain: nf5 replication + closure readiness + bundle summary."""
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

DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_v1_post_triangle_chain_v1_latest.json"
SCHEMA = "rq024_btc_lens_v1_post_triangle_chain_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script: str, *extra: str) -> tuple[int, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *extra]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    steps: list[dict[str, Any]] = []
    scripts = [
        ("nf5_wf_replication", "run_rq024_btc_lens_v1_nf5_wf_replication_v1.py"),
        ("closure_readiness", "build_rq024_research_closure_readiness_v1.py"),
        ("triangular_refresh", "build_rq024_btc_lens_v1_triangular_validation_v1.py"),
    ]
    exit_codes: list[int] = []
    for step_name, script in scripts:
        rc, log = _run_py(script)
        exit_codes.append(rc)
        steps.append(
            {
                "step": step_name,
                "script": script,
                "exit_code": rc,
                "output_tail": log.splitlines()[-4:] if log else [],
            }
        )

    readiness = _load(ROOT / "docs/final/artifacts/rq024_research_closure_readiness_v1_latest.json")
    nf5 = _load(ROOT / "reports/rq024_btc_lens_v1_nf5_wf_replication_v1_latest.json")
    triangle = _load(ROOT / "reports/rq024_btc_lens_v1_triangular_validation_v1_latest.json")

    bundle = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "steps": steps,
        "nf5_replication_met": (nf5.get("dod_nf5_replication") or {}).get("met"),
        "triangle_met": (triangle.get("triangle") or {}).get("met"),
        "mechanics_bundle_ok": readiness.get("mechanics_bundle_ok"),
        "closure_allowed": readiness.get("closure_allowed"),
        "verdict_ko": readiness.get("verdict_ko"),
        "next_human_gate": readiness.get("next_human_gate"),
        "chain_ok": all(c == 0 for c in exit_codes),
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(
        f"chain_ok={bundle['chain_ok']} mechanics_ok={bundle['mechanics_bundle_ok']} "
        f"closure_allowed={bundle['closure_allowed']}"
    )
    return 0 if bundle["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
