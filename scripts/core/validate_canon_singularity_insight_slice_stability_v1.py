#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate slice stability monitor output.")
    ap.add_argument(
        "--input-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_slice_stability_v1.json",
    )
    ap.add_argument("--max-slice-change-count", type=int, default=5)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_slice_stability_quality_gate_v1.json",
    )
    args = ap.parse_args()

    checks = {"schema_ok": False, "events_ok": False, "slice_change_threshold_ok": False}
    base = {
        "schema": "original_corpus_regime_singularity_canon_insight_slice_stability_quality_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "input_json": str(args.input_json),
            "max_slice_change_count": int(args.max_slice_change_count),
        },
    }
    try:
        data = _read_json(Path(args.input_json))
        checks["schema_ok"] = data.get("schema") == "original_corpus_regime_singularity_canon_insight_slice_stability_v1"
        events = int((data.get("counts") or {}).get("events_in_window", 0))
        checks["events_ok"] = events >= 2
        slice_change_count = int((data.get("counts") or {}).get("slice_change_count", 0))
        checks["slice_change_threshold_ok"] = slice_change_count <= int(args.max_slice_change_count)
        ok = all(checks.values())
        out = {
            **base,
            "status": "pass" if ok else "fail",
            "checks": checks,
            "metrics": {"events_in_window": events, "slice_change_count": slice_change_count},
        }
        _write(Path(args.output_json), out)
        if ok:
            print("OK: insight slice stability quality gate pass")
            return 0
        print("FAIL: insight slice stability quality gate fail", file=sys.stderr)
        return 1
    except Exception as e:
        _write(Path(args.output_json), {**base, "status": "fail", "error": str(e), "checks": checks})
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

