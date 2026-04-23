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
    ap = argparse.ArgumentParser(description="Validate canon weekly brief artifact.")
    ap.add_argument(
        "--input-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_weekly_brief_v1.json",
    )
    ap.add_argument("--max-gate-fail", type=int, default=0)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_weekly_brief_quality_gate_v1.json",
    )
    args = ap.parse_args()

    checks = {"schema_ok": False, "counts_ok": False, "health_present_ok": False, "gate_fail_ok": False}
    base = {
        "schema": "original_corpus_regime_singularity_canon_weekly_brief_quality_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {"input_json": str(args.input_json), "max_gate_fail": int(args.max_gate_fail)},
    }
    try:
        data = _read_json(Path(args.input_json))
        checks["schema_ok"] = data.get("schema") == "original_corpus_regime_singularity_canon_weekly_brief_v1"
        c = data.get("counts") or {}
        checks["counts_ok"] = int(c.get("insight_events_in_window", 0)) >= 1 and int(c.get("gate_events_in_window", 0)) >= 1
        checks["health_present_ok"] = bool((data.get("highlights") or {}).get("health_level"))
        gate_fail = int(c.get("gate_fail_count", 0))
        checks["gate_fail_ok"] = gate_fail <= int(args.max_gate_fail)
        ok = all(checks.values())
        out = {**base, "status": "pass" if ok else "fail", "checks": checks, "metrics": {"gate_fail_count": gate_fail}}
        _write(Path(args.output_json), out)
        if ok:
            print("OK: weekly brief quality gate pass")
            return 0
        print("FAIL: weekly brief quality gate fail", file=sys.stderr)
        return 1
    except Exception as e:
        _write(Path(args.output_json), {**base, "status": "fail", "error": str(e), "checks": checks})
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

