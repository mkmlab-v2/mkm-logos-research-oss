#!/usr/bin/env python3
"""Build runtime kmh signal artifact used by daily governance chain."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "emotion_state_kmh_runtime_signal_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--z-km", type=float, default=0.0)
    ap.add_argument("--source", default="manual_runtime_seed")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    z_km = _clip(float(args.z_km), -1.0, 1.0)
    out = {
        "schema": "emotion_state_kmh_runtime_signal_v1",
        "generated_at_utc": _iso_now(),
        "source": str(args.source),
        "z_km": z_km,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "z_km": z_km}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
