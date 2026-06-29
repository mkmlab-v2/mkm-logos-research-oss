#!/usr/bin/env python3
"""Build Cloud Shell one-liner: extract productive burn pkg + resume gen-lang lanes."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAR = ROOT / "reports" / "gcp_productive_burn_shell_pkg_v1.tar.gz"
OUT = ROOT / "reports" / "gcp_productive_burn_resume_cloudshell_paste_v1.txt"
META = ROOT / "reports" / "gcp_productive_burn_resume_paste_meta_v1_latest.json"


def main() -> int:
    if not TAR.is_file():
        raise SystemExit(f"missing tar: {TAR}")
    b64 = base64.b64encode(TAR.read_bytes()).decode("ascii")
    gcs_resume = (
        "gcloud storage cp gs://gen-lang-client-burn-wave2/productive_burn_shell_pkg_v1.tar.gz /tmp/pb_pkg.tar.gz && "
        "tar xzf /tmp/pb_pkg.tar.gz -C ~ && "
        "sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py && "
        "test -f ~/gcp_productive_burn_lane_runner_v1.py || { echo 'INSTALL FAIL: runner missing after tar'; exit 1; } && "
        "chmod +x ~/gcp_productive_burn_resume_genlang.sh && "
        "bash ~/gcp_productive_burn_resume_genlang.sh"
    )
    b64_resume = (
        f"printf '%s' '{b64}' | base64 -d > /tmp/pb_pkg.tar.gz && "
        "tar xzf /tmp/pb_pkg.tar.gz -C ~ && "
        "sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py && "
        "test -f ~/gcp_productive_burn_lane_runner_v1.py || { echo 'INSTALL FAIL: runner missing (paste truncated?)'; exit 1; } && "
        "chmod +x ~/gcp_productive_burn_resume_genlang.sh && "
        "bash ~/gcp_productive_burn_resume_genlang.sh"
    )
    gcs_out = ROOT / "reports" / "gcp_productive_burn_resume_cloudshell_gcs_v1.txt"
    gcs_out.write_text(gcs_resume + "\n", encoding="utf-8")
    OUT.write_text(b64_resume + "\n", encoding="utf-8")
    cmd = gcs_resume
    meta = {
        "schema": "gcp_productive_burn_resume_paste_meta_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "paste_chars": len(b64_resume),
        "gcs_resume_chars": len(gcs_resume),
        "gcs_resume_path": str(gcs_out.relative_to(ROOT)).replace("\\", "/"),
        "preferred": "gcs_resume_path (avoid base64 truncation in Cloud Shell)",
        "tar_bytes": TAR.stat().st_size,
        "paste_path": str(OUT.relative_to(ROOT)).replace("\\", "/"),
    }
    META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
