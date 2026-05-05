#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_paths(obj: Any):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_paths(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_paths(item)
    elif isinstance(obj, str):
        yield obj


def _is_btrack_path(path_str: str) -> bool:
    x = path_str.lower().replace("\\", "/")
    return ("btrack" in x) or ("trackb" in x)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail gate when A-track inputs are contaminated by B-track paths.")
    ap.add_argument("--a-track-json", default="docs/final/artifacts/a_track_go_nogo_status_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/mkm_atrack_btrack_contamination_gate_latest.json")
    ap.add_argument("--strict-exit", action="store_true", help="Return exit 1 on contamination (default true behavior).")
    args = ap.parse_args()

    p_atrack = resolve(args.a_track_json)
    out_path = resolve(args.output_json)
    if not p_atrack.is_file():
        raise SystemExit(f"missing a-track json: {p_atrack}")

    data = json.loads(p_atrack.read_text(encoding="utf-8-sig"))
    input_paths = data.get("meta", {}).get("input_paths", {})
    optional_paths = data.get("meta", {}).get("optional_input_paths", {})

    contaminated = []
    for p in _iter_paths(input_paths):
        if _is_btrack_path(p):
            contaminated.append({"scope": "input_paths", "path": p})
    for p in _iter_paths(optional_paths):
        if _is_btrack_path(p):
            contaminated.append({"scope": "optional_input_paths", "path": p})

    status = "FAIL_CONTAMINATION" if contaminated else "PASS_CLEAN"
    payload = {
        "schema": "mkm_atrack_btrack_contamination_gate_v1",
        "generated_at_utc": utc_now(),
        "input_a_track_json": str(p_atrack),
        "status": status,
        "contamination_count": len(contaminated),
        "contaminated_paths": contaminated,
        "policy": {
            "rule": "A-track decision inputs must not include B-track-only paths.",
            "auto_bridge_allowed": False,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))

    if contaminated:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
