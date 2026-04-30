#!/usr/bin/env python3
"""Build indicator snapshot for L0 geopolitical/macro warning policy."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "l0_geopolitical_macro_warning_policy_template_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "l0_geopolitical_macro_indicator_snapshot_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument(
        "--manual-overrides-json",
        type=Path,
        default=None,
        help="Optional JSON object: {indicator_values:{...}} or flat {indicator_id:value}.",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    policy = _load_json(args.policy_json)
    indicators = policy.get("indicators") or []
    ids = [str(x.get("id") or "").strip() for x in indicators if isinstance(x, dict)]
    ids = [x for x in ids if x]

    values: dict[str, float] = {iid: 0.0 for iid in ids}
    override_count = 0
    if args.manual_overrides_json and args.manual_overrides_json.is_file():
        raw = _load_json(args.manual_overrides_json)
        src = raw.get("indicator_values") if isinstance(raw.get("indicator_values"), dict) else raw
        if isinstance(src, dict):
            for iid in ids:
                if iid in src:
                    try:
                        values[iid] = float(src[iid])
                        override_count += 1
                    except (TypeError, ValueError):
                        pass

    quality = "LOW_PLACEHOLDER" if override_count == 0 else "MIXED_MANUAL"
    out = {
        "schema": "l0_geopolitical_macro_indicator_snapshot_v1",
        "generated_at_utc": _now(),
        "policy_ref": str(args.policy_json),
        "indicator_values": values,
        "meta": {
            "indicator_count": len(ids),
            "overrides_applied": override_count,
            "data_quality": quality,
            "note": "Default zeros are placeholders; provide --manual-overrides-json for live values.",
        },
    }
    _write_json(args.out, out)
    print(f"WROTE: {args.out}")
    print(f"overrides_applied={override_count} data_quality={quality}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

