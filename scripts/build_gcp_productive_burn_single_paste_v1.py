#!/usr/bin/env python3
"""Build single-line Cloud Shell paste: base64 tar.gz + extract + bootstrap."""

from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAR = ROOT / "reports" / "gcp_productive_burn_shell_pkg_v1.tar.gz"
OUT = ROOT / "reports" / "gcp_productive_burn_SINGLE_PASTE_v1.sh"


def main() -> int:
    if not TAR.is_file():
        raise SystemExit(f"missing tar: {TAR}")
    b64 = base64.b64encode(TAR.read_bytes()).decode("ascii")
    cmd = (
        "set -e; "
        "pkill -f 'wave3_burn|gcp_max_burn|gcp_burn\\.sh|gcp_max_after' 2>/dev/null || true; "
        "sleep 2; "
        f"printf '%s' '{b64}' | base64 -d > /tmp/pb_pkg.tar.gz && "
        "tar xzf /tmp/pb_pkg.tar.gz -C ~ && "
        "sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py 2>/dev/null || true; "
        "chmod +x ~/gcp_productive_burn_deploy.sh ~/gcp_productive_burn_bootstrap.sh; "
        "bash ~/gcp_productive_burn_bootstrap.sh; "
        "echo STATUS; pgrep -af 'gcp_productive|productive_burn' || true; "
        "ls -la ~/productive_burn_logs 2>/dev/null | head -8"
    )
    OUT.write_text(cmd + "\n", encoding="utf-8")
    chunk = 5500
    parts_dir = ROOT / "reports" / "gcp_productive_burn_SINGLE_PASTE_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    prelude = (
        "set -e; pkill -f 'wave3_burn|gcp_max_burn|gcp_burn\\.sh|gcp_max_after' 2>/dev/null || true; "
        "sleep 2; rm -f /tmp/pb.b64 /tmp/pb_pkg.tar.gz; : > /tmp/pb.b64; "
    )
    (parts_dir / "00_prelude.sh").write_text(prelude + "\n", encoding="utf-8")
    for i in range(0, len(b64), chunk):
        part = b64[i : i + chunk]
        idx = i // chunk
        (parts_dir / f"{idx+1:02d}_b64_append.sh").write_text(
            f"printf '%s' '{part}' >> /tmp/pb.b64\n", encoding="utf-8"
        )
    epilogue = (
        "base64 -d /tmp/pb.b64 > /tmp/pb_pkg.tar.gz && tar xzf /tmp/pb_pkg.tar.gz -C ~ && "
        "sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py 2>/dev/null || true; "
        "chmod +x ~/gcp_productive_burn_deploy.sh ~/gcp_productive_burn_bootstrap.sh; "
        "bash ~/gcp_productive_burn_bootstrap.sh; echo STATUS; pgrep -af 'gcp_productive|productive_burn' || true; "
        "ls -la ~/productive_burn_logs 2>/dev/null | head -8"
    )
    (parts_dir / "99_epilogue.sh").write_text(epilogue + "\n", encoding="utf-8")
    print(f"chars={len(cmd)} path={OUT} parts={len(list(parts_dir.glob('*.sh')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
