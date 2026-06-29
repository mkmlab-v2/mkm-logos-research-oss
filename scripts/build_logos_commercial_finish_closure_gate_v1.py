#!/usr/bin/env python3
"""Finish-tier closure gate atop commercial-depth (MACULA + DSS + integration) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRESETS = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/logos_commercial_finish_closure_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> dict[str, Any]:
    depth = _load(ROOT / "docs/final/artifacts/logos_commercial_depth_closure_v1_latest.json")
    macula = _load(ROOT / "reports/logos_macula_themed_ingest_v1_latest.json")
    dss_lane = _load(ROOT / "reports/dss_apocrypha_shadow_lane_v1_latest.json")
    integration = _load(ROOT / "reports/logos_track_b_integration_closure_v1_latest.json")
    presets = _load(PRESETS)
    theme_count = len(presets.get("themes") or {})
    macula_themes = len(macula.get("themes") or {})

    checks = {
        "commercial_depth_closure": {
            "passed": depth.get("closure_ok") is True,
            "value": depth.get("closure_ok"),
        },
        "macula_theme_coverage": {
            "passed": macula_themes >= theme_count and theme_count >= 12,
            "value": macula_themes,
            "target": theme_count,
        },
        "macula_edges_built": {
            "passed": int(macula.get("edges_built") or 0) >= 1500,
            "value": macula.get("edges_built"),
            "target": 1500,
        },
        "dss_apocrypha_shadow_lane": {
            "passed": dss_lane.get("ok") is True,
            "value": dss_lane.get("ok"),
        },
        "integration_closure": {
            "passed": integration.get("ok") is True,
            "value": integration.get("ok"),
        },
    }
    finish_ok = all(c.get("passed") for c in checks.values())

    return {
        "schema": "logos_commercial_finish_closure_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "finish_ok": finish_ok,
        "finish_tier": "commercial_finish_complete" if finish_ok else "commercial_finish_in_progress",
        "checks": checks,
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_trigger": False,
            "ms_headline_merge_forbidden": True,
            "logos_core_mutation_forbidden": True,
        },
        "reproduce": "py scripts/build_logos_commercial_finish_closure_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "finish_ok": doc["finish_ok"], "tier": doc["finish_tier"]}, ensure_ascii=False))
    return 0 if doc["finish_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
