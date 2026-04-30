from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Promote Paddle onboarding status to COMPLETED with guards.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--note", default="Paddle onboarding finished and verified.")
    p.add_argument("--apply", action="store_true", help="Write COMPLETED status when gates pass.")
    args = p.parse_args()

    root = Path(args.workspace_root)
    art = root / "docs" / "final" / "artifacts"

    acceptance = _read_json(art / "mkm_trackc_operational_acceptance_latest.json")
    handoff_guard = _read_json(art / "mkm_trackc_client_handoff_guard_latest.json")
    paddle = _read_json(art / "paddle_onboarding_status_latest.json")

    failures: List[str] = []
    if acceptance.get("status") != "PASS":
        failures.append("acceptance_not_pass")
    if handoff_guard.get("passed") is not True:
        failures.append("handoff_guard_not_pass")
    if paddle.get("status") != "VERIFICATION_PENDING":
        failures.append("paddle_status_not_verification_pending")

    report = {
        "schema": "paddle_onboarding_completion_promotion_report_v1",
        "generated_at_utc": _utc_now(),
        "ready_to_promote": len(failures) == 0,
        "apply_requested": args.apply,
        "failures": failures,
        "current_paddle_status": paddle.get("status"),
    }

    if args.apply and not failures:
        next_payload = {
            "schema": "paddle_onboarding_status_v1",
            "generated_at_utc": _utc_now(),
            "status": "COMPLETED",
            "note": args.note,
            "runbook_ref": "docs/final/artifacts/PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md",
        }
        _write_json(art / "paddle_onboarding_status_latest.json", next_payload)
        (art / "paddle_onboarding_status_latest.md").write_text(
            "\n".join(
                [
                    "# Paddle Onboarding Status",
                    "",
                    f"- generated_at_utc: `{next_payload['generated_at_utc']}`",
                    f"- status: `{next_payload['status']}`",
                    f"- note: {next_payload['note']}",
                    f"- runbook_ref: `{next_payload['runbook_ref']}`",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        report["applied"] = True
    else:
        report["applied"] = False

    out = art / "paddle_onboarding_completion_promotion_latest.json"
    _write_json(out, report)
    print(f"promotion report written: {out}")
    print(f"ready_to_promote={report['ready_to_promote']} applied={report['applied']}")
    return 0 if (not args.apply or report["applied"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
