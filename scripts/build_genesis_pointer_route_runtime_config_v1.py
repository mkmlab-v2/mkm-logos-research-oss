#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
IN_DEFAULT = ART / "genesis_pointer_routing_decision_latest.json"
OUT_DEFAULT = ART / "genesis_pointer_route_runtime_config_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decision-json", type=Path, default=IN_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    decision_path = args.decision_json if args.decision_json.is_absolute() else ROOT / args.decision_json
    dec = _read_json(decision_path)
    decision = str(dec.get("decision", "HOLD_POINTER_ROUTE"))
    route_mode = str(dec.get("route_mode", "track_a_primary"))
    stats = dec.get("stats", {})

    pointer_enabled = decision == "ENABLE_POINTER_ROUTE"
    pointer_shadow = decision == "SHADOW_POINTER_ROUTE"

    config = {
        "schema": "genesis_pointer_route_runtime_config_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {"decision_json": str(decision_path)},
        "routing": {
            "decision": decision,
            "route_mode": route_mode,
            "pointer_enabled": pointer_enabled,
            "pointer_shadow": pointer_shadow,
            "track_a_primary": route_mode == "track_a_primary",
            "disable_switch_env": "GENESIS_POINTER_ROUTE_FORCE_DISABLE",
        },
        "observability": {
            "go_count": stats.get("go_count"),
            "watch_count": stats.get("watch_count"),
            "hold_count": stats.get("hold_count"),
            "go_ratio": stats.get("go_ratio"),
        },
        "notes": [
            "Runtime config is generated from policy decision artifact; do not edit manually.",
            "If disable env is set to 1, force fallback to track_a_primary at runtime.",
        ],
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "route_mode": route_mode,
                "pointer_enabled": pointer_enabled,
                "pointer_shadow": pointer_shadow,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
