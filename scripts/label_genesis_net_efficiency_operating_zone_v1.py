#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
IN_DEFAULT = ART / "genesis_sequence_net_efficiency_sensitivity_latest.json"
OUT_DEFAULT = ART / "genesis_sequence_net_efficiency_operating_zone_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _label(row: dict[str, Any], go_cut: float, watch_cut: float) -> tuple[str, str]:
    score = float(row.get("pointer_net_saving_rate_at_400_chars", -1.0))
    break_even = row.get("pointer_net_break_even_length_chars")
    if score >= go_cut and (isinstance(break_even, int) and break_even <= 20):
        return "GO", "high_net_saving_and_low_break_even"
    if score >= watch_cut and (isinstance(break_even, int) and break_even <= 120):
        return "WATCH", "marginal_or_conditioned_efficiency"
    return "HOLD", "insufficient_net_efficiency_or_high_break_even"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-json", type=Path, default=IN_DEFAULT)
    ap.add_argument("--go-cut", type=float, default=0.99)
    ap.add_argument("--watch-cut", type=float, default=0.95)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    in_path = args.in_json if args.in_json.is_absolute() else ROOT / args.in_json
    doc = _read_json(in_path)
    scenarios = doc.get("scenarios", [])

    labeled: list[dict[str, Any]] = []
    counts = {"GO": 0, "WATCH": 0, "HOLD": 0}
    for r in scenarios:
        zone, reason = _label(r, go_cut=args.go_cut, watch_cut=args.watch_cut)
        counts[zone] += 1
        rr = dict(r)
        rr["operating_zone"] = zone
        rr["zone_reason"] = reason
        labeled.append(rr)

    out_doc = {
        "schema": "genesis_sequence_net_efficiency_operating_zone_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "inputs": {
            "source_json": str(in_path),
            "go_cut": args.go_cut,
            "watch_cut": args.watch_cut,
        },
        "counts": counts,
        "scenarios": labeled,
        "summary": {
            "go_ratio": counts["GO"] / float(max(1, len(labeled))),
            "watch_ratio": counts["WATCH"] / float(max(1, len(labeled))),
            "hold_ratio": counts["HOLD"] / float(max(1, len(labeled))),
        },
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "counts": counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
