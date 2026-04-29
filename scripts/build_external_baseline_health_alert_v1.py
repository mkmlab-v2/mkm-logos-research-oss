#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.3, M:0.7}
# Balance: 88
# Purpose: Emit health alert only when health_check indicates unhealthy state.
# Keywords: health alert, unhealthy, artifacts
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build health alert artifact.")
    ap.add_argument("--health-check-json", default="docs/final/artifacts/external_bible_crossref_health_check_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_health_alert_latest.json")
    args = ap.parse_args()

    p_health = resolve(args.health_check_json)
    p_out = resolve(args.output_json)
    health = load_json(p_health)
    checks = health.get("checks", []) if isinstance(health.get("checks"), list) else []
    unhealthy = [c for c in checks if isinstance(c, dict) and not bool(c.get("healthy", False))]
    active = len(unhealthy) > 0

    out = {
        "schema": "external_bible_crossref_health_alert_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "active": active,
        "health_check_ref": str(p_health) if p_health.is_file() else None,
        "unhealthy_count": len(unhealthy),
        "unhealthy_artifacts": [u.get("artifact") for u in unhealthy],
    }
    p_out.parent.mkdir(parents=True, exist_ok=True)
    p_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(p_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
