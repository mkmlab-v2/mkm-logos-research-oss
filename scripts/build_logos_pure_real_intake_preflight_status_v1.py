#!/usr/bin/env python3
"""Check whether today's pure-real intake meets action-pack target."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_ACTION_PACK = ART / "logos_pure_real_action_pack_latest.json"
DEFAULT_NEWS_JSONL = ART / "news_observation_v1_latest.jsonl"
DEFAULT_OUT = ART / "logos_pure_real_intake_preflight_status_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            rows.append(json.loads(s))
        except Exception:
            continue
    return rows


def _date_part(v: str) -> str:
    s = str(v or "").strip()
    if not s:
        return ""
    return s[:10]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pure-real intake preflight status.")
    ap.add_argument("--action-pack-json", type=Path, default=DEFAULT_ACTION_PACK)
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS_JSONL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    action_pack = _load_json(args.action_pack_json)
    rows = _load_jsonl(args.news_jsonl)

    today_utc = str((action_pack.get("status") or {}).get("today_utc") or datetime.now(timezone.utc).date().isoformat())
    required_rows_today = int((action_pack.get("today_targets") or {}).get("recommended_total_rows_today") or 0)

    actual_rows_today = 0
    for r in rows:
        if bool(r.get("is_synthetic_source", False)):
            continue
        if _date_part(str(r.get("as_of_utc") or "")) == today_utc:
            actual_rows_today += 1

    shortage = max(0, required_rows_today - actual_rows_today)
    status = "PASS_INTAKE_READY" if shortage == 0 else "FAIL_NEED_MORE_ROWS"

    out = {
        "schema": "logos_pure_real_intake_preflight_status_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "today_utc": today_utc,
        "required_rows_today": required_rows_today,
        "actual_rows_today": actual_rows_today,
        "shortage_rows_today": shortage,
        "status": status,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "status": status,
                "shortage_rows_today": shortage,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

