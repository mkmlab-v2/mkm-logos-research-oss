#!/usr/bin/env python3
"""Pack productive burn Cloud Shell deploy files into tar.gz + upload helper."""

from __future__ import annotations

import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_TAR = ROOT / "reports" / "gcp_productive_burn_shell_pkg_v1.tar.gz"
META = ROOT / "reports" / "gcp_productive_burn_shell_pkg_meta_v1_latest.json"
GCS_URI = "gs://gen-lang-client-burn-wave2/productive_burn_shell_pkg_v1.tar.gz"

FILES = [
    ("gcp_productive_burn_lane_runner_v1.py", ROOT / "scripts" / "gcp_productive_burn_lane_runner_v1.py"),
    ("gcp_productive_burn_deploy.sh", ROOT / "scripts" / "gcp_free_trial_cloud_shell_productive_burn_deploy_v1.sh"),
    ("gcp_productive_burn_resume_genlang.sh", ROOT / "scripts" / "gcp_productive_burn_resume_genlang_v1.sh"),
    ("gcp_productive_burn_resume_post_iam_v1.sh", ROOT / "scripts" / "gcp_productive_burn_resume_post_iam_v1.sh"),
    ("gcp_productive_burn_resume_post_adc_v1.sh", ROOT / "scripts" / "gcp_productive_burn_resume_post_adc_v1.sh"),
    ("gcp_productive_burn_adc_smoke_v1.sh", ROOT / "scripts" / "gcp_productive_burn_adc_smoke_v1.sh"),
    ("gcp_productive_burn_unattended_cloudshell_v1.sh", ROOT / "scripts" / "gcp_productive_burn_unattended_cloudshell_v1.sh"),
    ("gcp_productive_burn_bootstrap.sh", ROOT / "scripts" / "gcp_productive_burn_cloudshell_bootstrap_v1.sh"),
    ("gcp_productive_burn_install_from_gcs_v1.sh", ROOT / "scripts" / "gcp_productive_burn_install_from_gcs_v1.sh"),
    ("fills_daily_compact_v1.json", ROOT / "reports" / "sandbox" / "fills_daily_compact_v1.json"),
]


def main() -> int:
    OUT_TAR.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(OUT_TAR, "w:gz") as tar:
        for arcname, path in FILES:
            if not path.is_file():
                raise SystemExit(f"missing: {path}")
            tar.add(path, arcname=arcname)

    cloud_shell_oneliner = (
        "pkill -f 'wave3_burn|gcp_max_burn|gcp_burn' 2>/dev/null; sleep 1; "
        f"gcloud storage cp {GCS_URI} /tmp/pb_pkg.tar.gz && "
        "tar xzf /tmp/pb_pkg.tar.gz -C ~ && "
        "sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py && "
        "chmod +x ~/gcp_productive_burn_deploy.sh ~/gcp_productive_burn_bootstrap.sh && "
        "bash ~/gcp_productive_burn_bootstrap.sh"
    )
    resume_oneliner = (
        f"gcloud storage cp {GCS_URI} /tmp/pb_pkg.tar.gz && "
        "tar xzf /tmp/pb_pkg.tar.gz -C ~ && "
        "sed -i 's/\\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py && "
        "test -f ~/gcp_productive_burn_lane_runner_v1.py || { echo 'INSTALL FAIL: runner missing after tar'; exit 1; } && "
        "chmod +x ~/gcp_productive_burn_resume_genlang.sh && "
        "bash ~/gcp_productive_burn_resume_genlang.sh"
    )

    upload_cmd = f"gcloud storage cp {OUT_TAR.as_posix()} {GCS_URI}"

    meta = {
        "schema": "gcp_productive_burn_shell_pkg_meta_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tar_path": str(OUT_TAR.relative_to(ROOT)).replace("\\", "/"),
        "tar_bytes": OUT_TAR.stat().st_size,
        "gcs_uri": GCS_URI,
        "upload_from_cloud_shell_as_jema12": upload_cmd,
        "deploy_oneliner_after_upload": cloud_shell_oneliner,
        "resume_oneliner_after_upload": resume_oneliner,
        "account_note": "Use jema12@mkmlife.com in Cloud Shell — NOT admin@no1kmedi.com",
    }
    META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (ROOT / "reports" / "gcp_productive_burn_cloudshell_oneliner_v1.txt").write_text(
        cloud_shell_oneliner + "\n", encoding="utf-8"
    )
    (ROOT / "reports" / "gcp_productive_burn_resume_oneliner_v1.txt").write_text(
        resume_oneliner + "\n", encoding="utf-8"
    )
    print(json.dumps({"tar": str(OUT_TAR), "bytes": meta["tar_bytes"], "gcs": GCS_URI}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
