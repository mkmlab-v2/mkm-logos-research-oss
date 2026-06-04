#!/usr/bin/env python3
"""[HYPO] P1 aux shard ping: manifest + optional client probe (port 19877)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/p1_shard_ping_aux_v1_latest.json"
)
MANIFEST_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/p1_aux_distributed_manifest_v1_latest.json"
)
AUX_DROP = ROOT / "experiments/nextgen_clean_slate_cpu_v1/aux_drop"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aux-ip", default="180.224.2.24")
    ap.add_argument("--port", type=int, default=19877)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--payload-kb", type=int, default=256)
    ap.add_argument("--skip-probe", action="store_true")
    args = ap.parse_args()

    manifest = {
        "schema": "nextgen_p1_aux_distributed_manifest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "aux_ip": args.aux_ip,
        "port": args.port,
        "aux_server_cmd_on_share": (
            "Z:\\nextgen_cpu_aux\\RUN_P1_SERVER_ON_AUX.cmd "
            "(after deploy_nextgen_clean_slate_cpu_aux_drop_v1.py)"
        ),
        "rtt_server_cmd": "Z:\\nextgen_cpu_aux\\RUN_RTT_SERVER_ON_AUX.cmd",
        "primary_probe_command": (
            f"py scripts/run_nextgen_clean_slate_cpu_p1_shard_ping_v1.py "
            f"--mode client --host {args.aux_ip} --port {args.port} "
            f"--shard-index 1 --rounds {args.rounds} --payload-kb {args.payload_kb} "
            f"--out-json experiments/nextgen_clean_slate_cpu_v1/results/"
            f"p1_shard_ping_aux_v1_latest.json"
        ),
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    probe_exit = 0
    probe_doc = None
    if not args.skip_probe:
        cmd = [
            sys.executable,
            str(ROOT / "scripts/run_nextgen_clean_slate_cpu_p1_shard_ping_v1.py"),
            "--mode",
            "client",
            "--host",
            args.aux_ip,
            "--port",
            str(args.port),
            "--shard-index",
            "1",
            "--rounds",
            str(args.rounds),
            "--payload-kb",
            str(args.payload_kb),
            "--out-json",
            str(OUT),
        ]
        timeout_s = max(30, int(args.rounds) * 12 + 10)
        try:
            probe_exit = subprocess.run(
                cmd, cwd=str(ROOT), timeout=timeout_s
            ).returncode
        except subprocess.TimeoutExpired:
            probe_exit = 124
        if OUT.is_file():
            probe_doc = json.loads(OUT.read_text(encoding="utf-8-sig"))

    summary = {
        "wrote_manifest": str(MANIFEST_OUT),
        "probe_exit": probe_exit,
        "probe_ok": probe_exit == 0,
        "probe_pointer": str(OUT.relative_to(ROOT)).replace("\\", "/") if OUT.is_file() else None,
        "rounds_ok": (probe_doc or {}).get("measurement", {}).get("rounds_ok"),
        "aux_drop_has_p1": (AUX_DROP / "RUN_P1_SERVER_ON_AUX.cmd").is_file(),
    }
    ok = probe_exit == 0 and int(summary.get("rounds_ok") or 0) > 0
    summary["probe_ok"] = ok
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
