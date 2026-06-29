#!/usr/bin/env python3
"""Base64 paste for browser Cloud Shell (no GCS) — post-IAM P4 resume."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAR = ROOT / "reports" / "gcp_productive_burn_shell_pkg_v1.tar.gz"
OUT = ROOT / "reports" / "gcp_productive_burn_browser_cloudshell_paste_v1.txt"


def main() -> int:
    if not TAR.is_file():
        raise SystemExit(f"missing: {TAR}")
    b64 = base64.b64encode(TAR.read_bytes()).decode("ascii")
    tail = (
        "tar xzf /tmp/pb_pkg.tar.gz -C ~ && "
        "sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py && "
        "chmod +x ~/gcp_productive_burn_resume_post_iam_v1.sh && "
        "pip install -q google-genai && "
        "bash ~/gcp_productive_burn_resume_post_iam_v1.sh"
    )
    cmd = f"printf '%s' '{b64}' | base64 -d > /tmp/pb_pkg.tar.gz && {tail}"
    OUT.write_text(cmd + "\n", encoding="utf-8")
    meta = {
        "schema": "gcp_productive_burn_browser_paste_meta_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "paste_path": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "paste_chars": len(cmd),
        "note": "Browser Cloud Shell admin_/jema12 — no GCS; paste entire file as one line",
    }
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
