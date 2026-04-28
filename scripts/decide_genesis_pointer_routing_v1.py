#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
IN_DEFAULT = ART / "genesis_sequence_net_efficiency_operating_zone_latest.json"
OUT_DEFAULT = ART / "genesis_pointer_routing_decision_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zone-json", type=Path, default=IN_DEFAULT)
    ap.add_argument("--enable-go-ratio-min", type=float, default=0.70)
    ap.add_argument("--enable-hold-count-max", type=int, default=0)
    ap.add_argument("--shadow-go-ratio-min", type=float, default=0.50)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    in_path = args.zone_json if args.zone_json.is_absolute() else ROOT / args.zone_json
    doc = _read_json(in_path)
    counts = doc.get("counts", {})
    total = max(1, int(sum(int(counts.get(k, 0)) for k in ("GO", "WATCH", "HOLD"))))
    go = int(counts.get("GO", 0))
    hold = int(counts.get("HOLD", 0))
    go_ratio = go / float(total)

    if go_ratio >= args.enable_go_ratio_min and hold <= args.enable_hold_count_max:
        decision = "ENABLE_POINTER_ROUTE"
        route_mode = "pointer_primary"
    elif go_ratio >= args.shadow_go_ratio_min:
        decision = "SHADOW_POINTER_ROUTE"
        route_mode = "pointer_shadow"
    else:
        decision = "HOLD_POINTER_ROUTE"
        route_mode = "track_a_primary"

    out_doc = {
        "schema": "genesis_pointer_routing_decision_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "inputs": {
            "zone_json": str(in_path),
            "enable_go_ratio_min": args.enable_go_ratio_min,
            "enable_hold_count_max": args.enable_hold_count_max,
            "shadow_go_ratio_min": args.shadow_go_ratio_min,
        },
        "stats": {
            "go_count": go,
            "watch_count": int(counts.get("WATCH", 0)),
            "hold_count": hold,
            "total": total,
            "go_ratio": go_ratio,
        },
        "decision": decision,
        "route_mode": route_mode,
        "safeguards": {
            "fallback_route_mode": "track_a_primary",
            "disable_switch_env": "GENESIS_POINTER_ROUTE_FORCE_DISABLE=1",
        },
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision, "route_mode": route_mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
