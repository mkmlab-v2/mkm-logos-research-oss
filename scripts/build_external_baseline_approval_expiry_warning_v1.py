#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.3, M:0.7}
# Balance: 88
# Purpose: Emit warning if approval expires soon or already expired.
# Keywords: approval, expiry, warning
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now() -> datetime:
    return datetime.now(timezone.utc)


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build approval expiry warning artifact.")
    ap.add_argument("--approval-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_approval_latest.json")
    ap.add_argument("--warn-within-hours", type=int, default=24)
    ap.add_argument("--renew-buffer-hours", type=int, default=6)
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_approval_expiry_warning_latest.json")
    args = ap.parse_args()

    p_approval = resolve(args.approval_json)
    p_out = resolve(args.output_json)
    approval = load_json(p_approval)
    approved = bool(approval.get("approved", False))
    expires_at = str(approval.get("expires_at_utc", "")).strip()
    exp_dt = parse(expires_at) if expires_at else None
    n = now()
    warn_hours = int(args.warn_within_hours)
    renew_buffer_hours = max(1, int(args.renew_buffer_hours))
    hours_left = ((exp_dt - n).total_seconds() / 3600.0) if exp_dt else None
    expired = bool(exp_dt and exp_dt <= n)
    expiring_soon = bool(exp_dt and not expired and hours_left is not None and hours_left <= warn_hours)
    active = approved and (expired or expiring_soon)

    out = {
        "schema": "external_bible_crossref_approval_expiry_warning_v1",
        "generated_at_utc": fmt(n),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "active": active,
        "approval_ref": str(p_approval) if p_approval.is_file() else None,
        "approved": approved,
        "expires_at_utc": expires_at or None,
        "expired": expired,
        "expiring_soon": expiring_soon,
        "hours_left": round(hours_left, 3) if hours_left is not None else None,
        "recommended_renew_before_hours": renew_buffer_hours,
        "renewal_due": bool(approved and exp_dt and hours_left is not None and hours_left <= renew_buffer_hours),
        "recommended_action": "reissue_approval" if bool(approved and (expired or expiring_soon)) else "none",
    }
    p_out.parent.mkdir(parents=True, exist_ok=True)
    p_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(p_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
