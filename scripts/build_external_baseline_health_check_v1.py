#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.3, M:0.7}
# Balance: 88
# Purpose: Read-only health check for latest baseline artifacts.
# Keywords: health check, artifacts, read-only
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def parse_time(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build read-only health check for latest artifacts.")
    ap.add_argument("--latest-index-json", default="docs/final/artifacts/external_bible_crossref_latest_index.json")
    ap.add_argument("--max-age-hours", type=int, default=168)
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_health_check_latest.json")
    args = ap.parse_args()

    idx_path = resolve(args.latest_index_json)
    out_path = resolve(args.output_json)
    idx = load_json(idx_path)
    arts = idx.get("artifacts", {}) if isinstance(idx.get("artifacts"), dict) else {}
    now = datetime.now(timezone.utc)
    max_age = int(args.max_age_hours)

    checks: list[dict[str, Any]] = []
    deferred_keys = {
        "threshold_apply_log_summary",
        "health_check",
        "health_alert",
        "approval_expiry_warning",
        "weekly_rollup",
    }
    for key, p in arts.items():
        if not p:
            if key in deferred_keys:
                checks.append({"artifact": key, "exists": False, "healthy": True, "reason": "deferred_generation_in_same_stage"})
            else:
                checks.append({"artifact": key, "exists": False, "healthy": False, "reason": "missing_path"})
            continue
        path = Path(str(p))
        if not path.is_file():
            checks.append({"artifact": key, "exists": False, "healthy": False, "reason": "file_not_found", "path": str(path)})
            continue
        generated_at = None
        age_hours = None
        healthy_age = True
        if path.suffix.lower() == ".json":
            doc = load_json(path)
            generated_at = str(doc.get("generated_at_utc", ""))
            dt = parse_time(generated_at) if generated_at else None
            if dt is not None:
                age_hours = (now - dt).total_seconds() / 3600.0
                healthy_age = age_hours <= max_age
        checks.append(
            {
                "artifact": key,
                "path": str(path),
                "exists": True,
                "generated_at_utc": generated_at,
                "age_hours": round(age_hours, 3) if age_hours is not None else None,
                "healthy": bool(healthy_age),
            }
        )

    out = {
        "schema": "external_bible_crossref_health_check_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "max_age_hours": max_age,
        "checks": checks,
        "all_healthy": all(bool(c.get("healthy", False)) for c in checks),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
