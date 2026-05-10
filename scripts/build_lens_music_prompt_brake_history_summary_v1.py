#!/usr/bin/env python3
"""Build M23 summary from lens music prompt overlay history log."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "lens_music_prompt_overlay_history_log.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_brake_history_summary_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path, max_rows: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = []
    for ln in lines[-max_rows:]:
        s = ln.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--max-rows", type=int, default=500)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _load_jsonl(args.history_log_jsonl, max_rows=max(1, int(args.max_rows)))
    n = len(rows)
    active = sum(1 for r in rows if bool(r.get("auto_brake_active")))
    gov_trigger = sum(1 for r in rows if bool(r.get("trigger_governance_watch")))
    smoke_trigger = sum(1 for r in rows if bool(r.get("trigger_smoke_eval_watch")))
    styles = Counter(str(r.get("answer_style", "unknown")) for r in rows)

    summary = {
        "schema": "lens_music_prompt_brake_history_summary_v1",
        "generated_at_utc": _utc_now(),
        "history_log_path": str(args.history_log_jsonl.resolve()),
        "rows_scanned": n,
        "auto_brake_active_count": active,
        "auto_brake_active_rate": round((active / n) if n else 0.0, 6),
        "trigger_counts": {
            "governance_watch": gov_trigger,
            "smoke_eval_watch": smoke_trigger,
        },
        "answer_style_counts": dict(styles),
        "state": "WATCH" if (n and active / n > 0.2) else "GO",
        "note": "M23 advisory summary for prompt auto-brake behavior.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "state": summary["state"], "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
