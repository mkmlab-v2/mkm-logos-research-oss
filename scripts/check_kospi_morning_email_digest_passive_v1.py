#!/usr/bin/env python3
"""Passive gate: after 08:30 KST, today's morning email digest artifact must be ok."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
DEFAULT_ARTIFACT = ROOT / "reports" / "kospi_morning_email_digest_latest.json"
MORNING_CUTOFF = time(8, 30)


def _parse_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # type: ignore[name-defined]
    return dt.astimezone(KST)


def evaluate(
    artifact_path: Path,
    *,
    now_kst: datetime | None = None,
    force: bool = False,
) -> dict:
    now = now_kst or datetime.now(KST)
    today = now.date()
    out: dict = {
        "schema": "kospi_morning_email_digest_passive_v1",
        "checked_at_kst": now.isoformat(),
        "artifact_path": str(artifact_path),
        "morning_cutoff_kst": MORNING_CUTOFF.isoformat(),
    }

    if not force and now.time() < MORNING_CUTOFF:
        out.update(
            {
                "status": "skipped",
                "ok": True,
                "reason": "before_morning_cutoff_0830_kst",
            }
        )
        return out

    if not artifact_path.is_file():
        out.update({"status": "fail", "ok": False, "reason": "artifact_missing"})
        return out

    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        out.update({"status": "fail", "ok": False, "reason": f"artifact_unreadable:{exc}"})
        return out

    generated_raw = str(
        payload.get("generated_at_kst")
        or payload.get("generated_at_utc")
        or payload.get("generated_at")
        or ""
    )
    generated = _parse_ts(generated_raw)
    if generated is None:
        out.update({"status": "fail", "ok": False, "reason": "missing_or_bad_timestamp"})
        return out

    digest_ok = bool(payload.get("ok"))
    result = str(payload.get("result") or "")
    dry_run = bool(payload.get("dry_run"))
    same_day = generated.date() == today

    if digest_ok and same_day and not dry_run:
        out.update(
            {
                "status": "pass",
                "ok": True,
                "reason": "today_digest_ok",
                "digest_result": result,
                "generated_at_kst": generated.isoformat(),
            }
        )
        return out

    reasons = []
    if not same_day:
        reasons.append(f"stale_date:{generated.date().isoformat()}")
    if not digest_ok:
        reasons.append(f"digest_not_ok:{payload.get('error') or result or 'unknown'}")
    if dry_run:
        reasons.append("dry_run_not_scheduled_send")
    out.update(
        {
            "status": "fail",
            "ok": False,
            "reason": ";".join(reasons) or "unknown",
            "digest_result": result,
            "generated_at_kst": generated.isoformat(),
        }
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Passive KOSPI morning email digest check")
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "kospi_morning_email_digest_passive_latest.json")
    parser.add_argument("--force", action="store_true", help="Check even before 08:30 KST")
    args = parser.parse_args()

    report = evaluate(args.artifact, force=args.force)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = report.get("status")
    ok = bool(report.get("ok"))
    print(f"KOSPI_MORNING_PASSIVE status={status} ok={ok} reason={report.get('reason')}")
    print(f"WROTE: {args.out}")

    if status == "fail":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
