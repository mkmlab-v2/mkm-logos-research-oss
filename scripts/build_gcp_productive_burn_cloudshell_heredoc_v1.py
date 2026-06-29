#!/usr/bin/env python3
"""Emit 2-step Cloud Shell heredoc pastes (runner + resume). No GCS/base64."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports"
FILES = [
    ("step0_stop_filler.sh", None),
    ("step1_paste_runner.sh", ROOT / "scripts" / "gcp_productive_burn_lane_runner_v1.py"),
    ("step2_paste_unattended.sh", ROOT / "scripts" / "gcp_productive_burn_unattended_cloudshell_v1.sh"),
    ("step3_verify.sh", None),
]


def heredoc_install(dest_name: str, src: Path) -> str:
    body = src.read_text(encoding="utf-8").replace("\r\n", "\n")
    return (
        f"cat > ~/{dest_name} <<'MKMEOF'\n"
        f"{body}"
        f"MKMEOF\n"
        f"chmod +x ~/{dest_name} 2>/dev/null || true\n"
        f"ls -la ~/{dest_name}\n"
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    step0 = (
        "pkill -f 'wave3_burn|gcp_max_burn|gcp_burn_watchdog|gcp_burn_phase2|gcp_burn' 2>/dev/null; sleep 1; "
        "mkdir -p ~/productive_burn_logs; echo step0_ok\n"
    )
    step1 = heredoc_install("gcp_productive_burn_lane_runner_v1.py", FILES[1][1])
    step2 = (
        heredoc_install("gcp_productive_burn_unattended_cloudshell_v1.sh", FILES[2][1])
        + "chmod +x ~/gcp_productive_burn_unattended_cloudshell_v1.sh\n"
        + "bash ~/gcp_productive_burn_unattended_cloudshell_v1.sh\n"
    )
    step3 = (
        "ls -la ~/gcp_productive_burn_lane_runner_v1.py ~/mkm_productive_burn_bundle_v1.json 2>/dev/null; "
        "pgrep -af gcp_productive_burn_lane_runner || echo NO_RUNNER_PROC; "
        "wc -l ~/productive_burn_logs/*.jsonl 2>/dev/null || echo NO_JSONL_YET\n"
    )

    (OUT / "gcp_productive_burn_cloudshell_step0_stop.sh").write_text(step0 + "\n", encoding="utf-8")
    (OUT / "gcp_productive_burn_cloudshell_step1_runner.sh").write_text(step1, encoding="utf-8")
    (OUT / "gcp_productive_burn_cloudshell_step2_resume.sh").write_text(step2, encoding="utf-8")
    (OUT / "gcp_productive_burn_cloudshell_step3_verify.sh").write_text(step3 + "\n", encoding="utf-8")

    auth_note = (
        "# Optional — only if you want GCS later:\n"
        "gcloud auth login --brief\n"
        "gcloud config set project gen-lang-client-0846393371\n"
    )
    (OUT / "gcp_productive_burn_cloudshell_auth_optional.txt").write_text(auth_note, encoding="utf-8")

    meta = {
        "schema": "gcp_productive_burn_cloudshell_heredoc_meta_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "step0_chars": len(step0),
        "step1_chars": len(step1),
        "step2_chars": len(step2),
        "order": [
            "gcp_productive_burn_cloudshell_step0_stop.sh",
            "gcp_productive_burn_cloudshell_step1_runner.sh",
            "gcp_productive_burn_cloudshell_step2_resume.sh",
            "gcp_productive_burn_cloudshell_step3_verify.sh",
        ],
        "note": "Paste each step file FULL into Cloud Shell. Prefer over base64 chunks. GCS one-liner optional first.",
    }
    (OUT / "gcp_productive_burn_cloudshell_heredoc_meta_v1_latest.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
