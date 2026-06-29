#!/usr/bin/env python3
"""Emit sequential Cloud Shell paste commands (chunked base64 decode)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "gcp_productive_burn_cloudshell_chunks"


def main() -> int:
    files = {
        "runner": ROOT / "scripts" / "gcp_productive_burn_lane_runner_v1.py",
        "deploy": ROOT / "scripts" / "gcp_free_trial_cloud_shell_productive_burn_deploy_v1.sh",
        "bootstrap": ROOT / "scripts" / "gcp_productive_burn_cloudshell_bootstrap_v1.sh",
        "compact": ROOT / "reports" / "sandbox" / "fills_daily_compact_v1.json",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    commands: list[str] = []
    mapping = {
        "runner": "~/gcp_productive_burn_lane_runner_v1.py",
        "deploy": "~/gcp_productive_burn_deploy.sh",
        "bootstrap": "~/gcp_productive_burn_bootstrap.sh",
        "compact": "~/fills_daily_compact_v1.json",
    }
    for key, path in files.items():
        b = base64.b64encode(path.read_bytes()).decode("ascii")
        chunk_size = 12000
        dest = mapping[key]
        if len(b) <= chunk_size:
            commands.append(f"printf '%s' '{b}' | base64 -d > {dest}")
        else:
            part_paths = []
            for i in range(0, len(b), chunk_size):
                part = b[i : i + chunk_size]
                part_file = OUT_DIR / f"{key}_b64_part{i // chunk_size}.txt"
                part_file.write_text(part, encoding="utf-8")
                part_paths.append(str(part_file))
                commands.append(f"printf '%s' '{part}' >> ~/upload_b64.tmp")
            commands.insert(
                len(commands) - len(part_paths),
                f"rm -f ~/upload_b64.tmp && : > ~/upload_b64.tmp",
            )
            commands.append(f"base64 -d ~/upload_b64.tmp > {dest} && rm -f ~/upload_b64.tmp")

    commands.append("sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py")
    commands.append("chmod +x ~/gcp_productive_burn_deploy.sh ~/gcp_productive_burn_bootstrap.sh")
    commands.append("bash ~/gcp_productive_burn_bootstrap.sh")

    for i, cmd in enumerate(commands, start=1):
        (OUT_DIR / f"cmd_{i:02d}.sh").write_text(cmd + "\n", encoding="utf-8")

    meta = {"commands": len(commands), "out_dir": str(OUT_DIR)}
    (OUT_DIR / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
