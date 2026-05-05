#!/usr/bin/env python3
"""Check sustained promotion gate from external anchor promotion history."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_HISTORY = ART / "external_bible_anchor_promotion_history_log.jsonl"
DEFAULT_OUT = ART / "external_bible_anchor_promotion_sustain_gate_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _streak_from_end(rows: list[dict[str, Any]], pred) -> int:
    n = 0
    for r in reversed(rows):
        if pred(r):
            n += 1
        else:
            break
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--required-pass-streak", type=int, default=3)
    ap.add_argument("--required-fail-streak-for-downgrade", type=int, default=2)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _read_jsonl(args.history_jsonl)

    def _is_mature_adopt_pass(r: dict[str, Any]) -> bool:
        ea = str(r.get("effective_action") or "")
        return ea in {"adopt_limited", "adopt_limited_strict"}

    pass_streak = _streak_from_end(
        rows,
        lambda r: str(r.get("promoted_status") or "") in {"PROMOTED_TIER1_CANDIDATES", "PROMOTED_TIER1_CANDIDATES_LATCHED"}
        and _is_mature_adopt_pass(r)
        and str(r.get("regression_status") or "") == "PASS",
    )
    fail_streak = _streak_from_end(
        rows,
        lambda r: str(r.get("effective_action") or "") == "monitor_only"
        or str(r.get("regression_status") or "") == "FAIL",
    )

    mature = pass_streak >= int(args.required_pass_streak)
    downgrade = fail_streak >= int(args.required_fail_streak_for_downgrade)
    status = "MATURE" if mature else ("DOWNGRADE_TRIGGER" if downgrade else "WARMUP")

    out = {
        "schema": "external_bible_anchor_promotion_sustain_gate_v1",
        "generated_at_utc": _iso_now(),
        "history_jsonl": str(args.history_jsonl).replace("\\", "/"),
        "required_pass_streak": int(args.required_pass_streak),
        "required_fail_streak_for_downgrade": int(args.required_fail_streak_for_downgrade),
        "current": {
            "history_rows": len(rows),
            "pass_streak": pass_streak,
            "fail_streak": fail_streak,
        },
        "status": status,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": status, "output_json": str(args.output_json).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
