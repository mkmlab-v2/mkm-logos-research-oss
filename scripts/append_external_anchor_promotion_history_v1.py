#!/usr/bin/env python3
"""Append external anchor promotion snapshot to history log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROMOTED = ART / "external_bible_anchor_tier1_promoted_latest.json"
DEFAULT_POLICY = ART / "external_bible_anchor_operating_policy_latest.json"
DEFAULT_REGRESSION = ART / "external_bible_anchor_post_promotion_regression_latest.json"
DEFAULT_HISTORY = ART / "external_bible_anchor_promotion_history_log.jsonl"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--promoted-json", type=Path, default=DEFAULT_PROMOTED)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--regression-json", type=Path, default=DEFAULT_REGRESSION)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument(
        "--overwrite-last-row",
        action="store_true",
        help="Replace the last JSONL row with this snapshot (after final policy sync; "
        "keeps history aligned with adopt_limited_strict upgrades).",
    )
    args = ap.parse_args()

    promoted = _read_json(args.promoted_json)
    policy = _read_json(args.policy_json)
    regression = _read_json(args.regression_json)

    row = {
        "schema": "external_bible_anchor_promotion_history_row_v1",
        "ts_utc": _iso_now(),
        "promoted_status": promoted.get("status"),
        "promoted_count": promoted.get("promoted_count"),
        "effective_action": policy.get("effective_action"),
        "regression_status": regression.get("status"),
    }
    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)

    if args.overwrite_last_row:
        rows_out: list[str] = []
        if args.history_jsonl.is_file():
            with args.history_jsonl.open("r", encoding="utf-8-sig") as fh:
                for line in fh:
                    s = line.strip()
                    if s:
                        rows_out.append(s)
        if rows_out:
            rows_out[-1] = json.dumps(row, ensure_ascii=False)
            args.history_jsonl.write_text("\n".join(rows_out) + "\n", encoding="utf-8")
        else:
            with args.history_jsonl.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    else:
        with args.history_jsonl.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "history_jsonl": str(args.history_jsonl).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
