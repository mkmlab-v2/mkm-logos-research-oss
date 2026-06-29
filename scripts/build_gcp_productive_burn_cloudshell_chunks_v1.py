#!/usr/bin/env python3
"""Split tar.gz base64 into 2 Cloud Shell paste chunks + GCS install one-liner."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAR = ROOT / "reports" / "gcp_productive_burn_shell_pkg_v1.tar.gz"
OUT_DIR = ROOT / "reports"
CHUNK_CHARS = 5500


def main() -> int:
    if not TAR.is_file():
        raise SystemExit(f"missing: {TAR}")

    b64 = base64.b64encode(TAR.read_bytes()).decode("ascii")
    mid = len(b64) // 2
    parts = [b64[:mid], b64[mid:]]

    tail = (
        "tar xzf /tmp/pb_pkg.tar.gz -C ~ && sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py && "
        "chmod +x ~/gcp_productive_burn_*.sh && pip install -q google-genai google-auth && "
        "bash ~/gcp_productive_burn_unattended_cloudshell_v1.sh"
    )
    gcs_install = (
        "gcloud storage cp gs://gen-lang-client-burn-wave2/productive_burn_shell_pkg_v1.tar.gz /tmp/pb_pkg.tar.gz && "
        + tail
    )

    chunk1 = (
        "pkill -f 'wave3_burn|gcp_max_burn|gcp_burn_watchdog|gcp_burn_phase2|gcp_burn' 2>/dev/null; sleep 1; "
        "rm -f /tmp/pb.b64; cat > /tmp/pb.b64 <<'B64EOF'\n" + parts[0] + "\nB64EOF"
    )
    chunk2 = (
        "cat >> /tmp/pb.b64 <<'B64EOF'\n" + parts[1] + "\nB64EOF\n"
        "base64 -d /tmp/pb.b64 > /tmp/pb_pkg.tar.gz && " + tail
    )

    (OUT_DIR / "gcp_productive_burn_cloudshell_gcs_install_v1.txt").write_text(gcs_install + "\n", encoding="utf-8")
    (OUT_DIR / "gcp_productive_burn_cloudshell_chunk1_v1.sh").write_text(chunk1 + "\n", encoding="utf-8")
    (OUT_DIR / "gcp_productive_burn_cloudshell_chunk2_v1.sh").write_text(chunk2 + "\n", encoding="utf-8")

    meta = {
        "schema": "gcp_productive_burn_cloudshell_chunks_meta_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "b64_total_chars": len(b64),
        "chunk1_chars": len(chunk1),
        "chunk2_chars": len(chunk2),
        "gcs_install_chars": len(gcs_install),
        "note": "Try gcs_install first on Cloud Shell; if 403/missing use chunk1 then chunk2",
    }
    (OUT_DIR / "gcp_productive_burn_cloudshell_chunks_meta_v1_latest.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
