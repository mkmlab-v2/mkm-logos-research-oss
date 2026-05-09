#!/usr/bin/env python3
"""Manual approval lock for myeongni weather fusion profile apply gate."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_PROFILE = ART / "myeongni_weather_fusion_profile_latest.json"
DEFAULT_LOCK = ART / "myeongni_weather_fusion_approval_lock_latest.json"
DEFAULT_LOG = REPORTS / "myeongni_weather_fusion_approval_log.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--lock-out", type=Path, default=DEFAULT_LOCK)
    ap.add_argument("--approval-log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--approve", action="store_true", help="Approve profile apply.")
    ap.add_argument("--reject", action="store_true", help="Reject profile apply.")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    if args.approve == args.reject:
        raise SystemExit("choose exactly one of --approve or --reject")

    profile = _read_json(args.profile_json)
    schema_ok = str(profile.get("schema") or "") == "myeongni_weather_fusion_profile_v1"
    rec = profile.get("recommended") if isinstance(profile.get("recommended"), dict) else {}
    rec_ok = all(
        k in rec for k in ("weight_direct", "weight_repro", "anchor_direct", "anchor_repro", "term_clip")
    )
    base_policy = profile.get("policy") if isinstance(profile.get("policy"), dict) else {}

    approved = bool(args.approve) and schema_ok and rec_ok
    decision = "approved" if approved else "rejected"
    reason = "manual_signoff_ok" if approved else "manual_reject_or_profile_invalid"

    profile["policy"] = {
        **base_policy,
        "allow_apply": bool(approved),
        "human_signoff_ack": bool(approved),
        "reviewer": args.reviewer,
        "reviewed_at_utc": _now(),
        "decision": decision,
        "decision_reason": reason,
    }
    args.profile_json.parent.mkdir(parents=True, exist_ok=True)
    args.profile_json.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lock = {
        "schema": "myeongni_weather_fusion_approval_lock_v1",
        "locked_at_utc": _now(),
        "profile_path": str(args.profile_json.resolve()),
        "decision": decision,
        "decision_reason": reason,
        "reviewer": args.reviewer,
        "profile_checks": {"schema_ok": schema_ok, "recommended_fields_ok": rec_ok},
        "policy_after_lock": profile["policy"],
        "note": args.note,
    }
    args.lock_out.parent.mkdir(parents=True, exist_ok=True)
    args.lock_out.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_jsonl(
        args.approval_log,
        {
            "ts_utc": lock["locked_at_utc"],
            "schema": lock["schema"],
            "decision": decision,
            "reviewer": args.reviewer,
            "profile_path": lock["profile_path"],
            "reason": reason,
        },
    )

    print(f"WROTE: {args.profile_json}")
    print(f"WROTE: {args.lock_out}")
    print(f"decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

