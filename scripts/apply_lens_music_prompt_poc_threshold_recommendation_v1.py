#!/usr/bin/env python3
"""Apply recommended threshold policy from latest sweep artifact."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_poc_threshold_sweep_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_poc_threshold_recommended_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sweep = _read_json(args.sweep_json)
    rec = dict(sweep.get("recommended_policy") or {})
    out = {
        "schema": "lens_music_prompt_poc_threshold_recommended_v1",
        "generated_at_utc": _utc_now(),
        "source_sweep_json": str(args.sweep_json).replace("\\", "/"),
        "decision": (sweep.get("summary") or {}).get("decision"),
        "policy_targets": {
            "min_samples": int(rec.get("min_samples") or 30),
            "style_delta_rate_min": float(rec.get("style_delta_rate_min") or 0.30),
            "overlay_style_match_rate_min": float(rec.get("overlay_style_match_rate_min") or 0.67),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": out["decision"], "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
