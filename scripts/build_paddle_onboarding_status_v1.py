from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    p = argparse.ArgumentParser(description="Build Paddle onboarding status artifact.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument(
        "--status",
        default=None,
        choices=["RUNBOOK_READY", "IN_PROGRESS", "BLOCKED", "VERIFICATION_PENDING", "COMPLETED"],
    )
    p.add_argument("--note", default=None)
    args = p.parse_args()

    root = Path(args.workspace_root)
    art = root / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)

    out_json = art / "paddle_onboarding_status_latest.json"
    prev = {}
    if out_json.exists():
        try:
            prev = json.loads(out_json.read_text(encoding="utf-8-sig"))
        except Exception:
            prev = {}

    effective_status = args.status or prev.get("status") or "RUNBOOK_READY"
    effective_note = (
        args.note
        if args.note is not None
        else prev.get("note") or "Use PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md workflow."
    )

    payload = {
        "schema": "paddle_onboarding_status_v1",
        "generated_at_utc": _utc_now(),
        "status": effective_status,
        "note": effective_note,
        "runbook_ref": "docs/final/artifacts/PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md",
    }

    out_md = art / "paddle_onboarding_status_latest.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Paddle Onboarding Status",
                "",
                f"- generated_at_utc: `{payload['generated_at_utc']}`",
                f"- status: `{payload['status']}`",
                f"- note: {payload['note']}",
                f"- runbook_ref: `{payload['runbook_ref']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"paddle status json written: {out_json}")
    print(f"paddle status md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
