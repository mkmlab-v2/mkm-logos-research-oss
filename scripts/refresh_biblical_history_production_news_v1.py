#!/usr/bin/env python3
"""Refresh production news ledger when 90d window is thin (platform + health ingest).

Idempotent: re-ingest only if lookback row count below threshold. research_only · [HYPO].
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROD = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_PLATFORM = ROOT / "reports/korea_platform_disinfo_news_articles_v1.json"
DEFAULT_HEALTH = ROOT / "reports/korea_health_infectious_news_articles_v1.json"
DEFAULT_OUT = ROOT / "reports/biblical_history_production_news_refresh_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_90d(path: Path, lookback_days: int) -> int:
    if not path.is_file():
        return 0
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=lookback_days)
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        ts_raw = row.get("as_of_utc") or row.get("published_utc")
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            continue
        if ts >= since:
            count += 1
    return count


def _ingest(articles_json: Path, *, prefix: str) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/ingest_korea_context_to_news_observation_v1.py"),
        "--articles-json",
        str(articles_json),
        "--source-id-prefix",
        prefix,
        "--dataset-partition",
        "train_holdout",
        "--validate",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    meta: dict[str, Any] = {"exit_code": proc.returncode, "articles_json": str(articles_json)}
    if proc.stdout.strip():
        try:
            meta.update(json.loads(proc.stdout.strip().splitlines()[-1]))
        except json.JSONDecodeError:
            meta["stdout_tail"] = proc.stdout[-500:]
    if proc.returncode != 0:
        meta["stderr_tail"] = (proc.stderr or "")[-500:]
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--production-jsonl", type=Path, default=DEFAULT_PROD)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--min-rows-90d", type=int, default=100, help="Re-ingest when 90d count is below this.")
    ap.add_argument("--force", action="store_true", help="Always re-ingest platform+health.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    before = _count_90d(args.production_jsonl, args.lookback_days)
    refreshed = False
    steps: list[dict[str, Any]] = []
    ok = True

    if args.force or before < args.min_rows_90d:
        for articles, prefix in (
            (DEFAULT_PLATFORM, "korea_platform_pr1"),
            (DEFAULT_HEALTH, "korea_health"),
        ):
            if not articles.is_file():
                steps.append({"source": str(articles), "status": "skipped_missing"})
                continue
            row = _ingest(articles, prefix=prefix)
            steps.append(row)
            if row.get("exit_code") != 0:
                ok = False
        refreshed = True

    after = _count_90d(args.production_jsonl, args.lookback_days)
    payload = {
        "schema": "biblical_history_production_news_refresh_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "lookback_days": args.lookback_days,
        "min_rows_90d": args.min_rows_90d,
        "production_jsonl": str(args.production_jsonl),
        "rows_90d_before": before,
        "rows_90d_after": after,
        "refreshed": refreshed,
        "steps": steps,
        "ok": ok,
        "track_a_promotion": "blocked",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "refreshed": refreshed, "rows_90d_after": after, "output": str(args.output_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
