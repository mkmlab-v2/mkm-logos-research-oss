#!/usr/bin/env python3
"""Generate Cloud Shell deploy command (runner + compact fills + bootstrap)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "gcp_productive_burn_cloudshell_deploy.txt"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> int:
    files = {
        "runner": ROOT / "scripts" / "gcp_productive_burn_lane_runner_v1.py",
        "deploy": ROOT / "scripts" / "gcp_free_trial_cloud_shell_productive_burn_deploy_v1.sh",
        "bootstrap": ROOT / "scripts" / "gcp_productive_burn_cloudshell_bootstrap_v1.sh",
        "compact": ROOT / "reports" / "sandbox" / "fills_daily_compact_v1.json",
    }
    for k, p in files.items():
        if not p.is_file():
            print(json.dumps({"error": f"missing {k}", "path": str(p)}))
            return 1

    parts = []
    parts.append(
        f"printf '%s' '{b64(files['runner'])}' | base64 -d > ~/gcp_productive_burn_lane_runner_v1.py"
    )
    parts.append(
        f"printf '%s' '{b64(files['deploy'])}' | base64 -d > ~/gcp_productive_burn_deploy.sh"
    )
    parts.append(
        f"printf '%s' '{b64(files['bootstrap'])}' | base64 -d > ~/gcp_productive_burn_bootstrap.sh"
    )
    parts.append(
        f"printf '%s' '{b64(files['compact'])}' | base64 -d > ~/fills_daily_compact_v1.json"
    )
    parts.append(
        "sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py"
    )
    parts.append("chmod +x ~/gcp_productive_burn_deploy.sh ~/gcp_productive_burn_bootstrap.sh")
    parts.append("bash ~/gcp_productive_burn_bootstrap.sh")

    cmd = " && ".join(parts)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(cmd + "\n", encoding="utf-8")

    meta_path = ROOT / "reports" / "gcp_productive_burn_deploy_meta_v1_latest.json"
    meta = {
        "schema": "gcp_productive_burn_deploy_meta_v1",
        "out_deploy_txt": str(OUT),
        "cmd_chars": len(cmd),
        "compact_bytes": files["compact"].stat().st_size,
        "runner_bytes": files["runner"].stat().st_size,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
