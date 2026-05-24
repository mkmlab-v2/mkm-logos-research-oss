#!/usr/bin/env python3
"""DECOY-P0 D1: verify mkmlife oracle-sphere route + components exist."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKM_LIFE = ROOT / "projects/mkm/mkm-life"
REQUIRED = (
    MKM_LIFE / "app/oracle-sphere/page.tsx",
    MKM_LIFE / "components/magic-orb/MagicOrbExperience.tsx",
    MKM_LIFE / "components/magic-orb/DisclaimerPanel.tsx",
    MKM_LIFE / "components/magic-orb/LensReportCard.tsx",
)
DEFAULT_OUT = ROOT / "docs/final/artifacts/decoy_d1_mkmlife_readiness_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = [{"path": str(p.relative_to(ROOT)).replace("\\", "/"), "exists": p.is_file()} for p in REQUIRED]
    ok = all(r["exists"] for r in rows) and MKM_LIFE.is_dir()
    doc = {
        "schema": "decoy_d1_mkmlife_readiness_v1",
        "mission_id": "DECOY-P0-D1",
        "generated_at_utc": _utc_now(),
        "route_hint": "/oracle-sphere",
        "files": rows,
        "d1_ok": ok,
        "track_wall": {"research_only": True, "no_live_payment": True, "demo_lenses_only": True},
    }
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
