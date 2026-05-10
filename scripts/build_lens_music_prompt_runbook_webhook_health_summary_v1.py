#!/usr/bin/env python3
"""M30: aggregate recent runbook webhook dispatch history into a health summary."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = ROOT / "reports" / "lens_music_prompt_poc_runbook_webhook_history.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_runbook_webhook_health_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_rows(path: Path, max_rows: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
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
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--max-rows", type=int, default=100)
    ap.add_argument("--top-skip-reasons", type=int, default=5)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _load_rows(args.history_jsonl, max_rows=max(1, int(args.max_rows)))
    n = len(rows)
    sent = skipped = failed = 0
    reason_ctr: Counter[str] = Counter()

    for r in rows:
        st = str(r.get("dispatch_status") or "").lower()
        if st == "sent":
            sent += 1
        elif st == "skipped":
            skipped += 1
            reason = str(r.get("skip_reason") or "unknown")
            reason_ctr[reason] += 1
        elif st == "failed":
            failed += 1

    top_n = max(1, int(args.top_skip_reasons))
    skip_top = [{"reason": k, "count": v} for k, v in reason_ctr.most_common(top_n)]

    out: dict[str, Any] = {
        "schema": "lens_music_prompt_runbook_webhook_health_v1",
        "generated_at_utc": _utc_now(),
        "history_log_path": str(args.history_jsonl.resolve()),
        "window_max_rows": int(args.max_rows),
        "samples_in_window": n,
        "counts": {"sent": sent, "skipped": skipped, "failed": failed},
        "rates": {
            "sent_rate": round(sent / n, 6) if n else 0.0,
            "skipped_rate": round(skipped / n, 6) if n else 0.0,
            "failed_rate": round(failed / n, 6) if n else 0.0,
        },
        "skip_reason_top": skip_top,
        "advisory_only": True,
        "track": "B",
    }
    if n == 0:
        out["state"] = "NODATA"
    elif failed > 0:
        out["state"] = "WATCH"
    elif skipped / n > 0.5:
        out["state"] = "WATCH"
    else:
        out["state"] = "GO"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "state": out["state"], "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
