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
    ap = argparse.ArgumentParser(description="Validate minimum canon insight artifact.")
    ap.add_argument(
        "--input-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_v1.json",
    )
    ap.add_argument("--min-rows", type=int, default=5)
    ap.add_argument("--min-commentary-len", type=int, default=30)
    ap.add_argument("--max-duplicate-ratio", type=float, default=0.5)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_quality_gate_v1.json",
    )
    args = ap.parse_args()

    checks = {
        "schema_ok": False,
        "rows_threshold_ok": False,
        "commentary_nonempty_ok": False,
        "evidence_present_ok": False,
        "duplicate_ratio_ok": False,
    }
    base = {
        "schema": "original_corpus_regime_singularity_canon_insight_minimum_quality_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "input_json": str(args.input_json),
            "min_rows": int(args.min_rows),
            "min_commentary_len": int(args.min_commentary_len),
            "max_duplicate_ratio": float(args.max_duplicate_ratio),
        },
    }
    try:
        data = _read_json(Path(args.input_json))
        if data.get("schema") == "original_corpus_regime_singularity_canon_insight_minimum_v1":
            checks["schema_ok"] = True
        rows = list(data.get("insights") or [])
        if len(rows) >= int(args.min_rows):
            checks["rows_threshold_ok"] = True

        commentaries = [str(r.get("commentary") or "").strip() for r in rows]
        if rows and all(len(c) >= int(args.min_commentary_len) for c in commentaries):
            checks["commentary_nonempty_ok"] = True

        if rows and all((r.get("evidence") or {}).get("source_summary") for r in rows):
            checks["evidence_present_ok"] = True

        uniq = len(set(commentaries)) if commentaries else 0
        dup_ratio = 0.0 if not commentaries else (1.0 - (uniq / len(commentaries)))
        if dup_ratio <= float(args.max_duplicate_ratio):
            checks["duplicate_ratio_ok"] = True

        ok = all(checks.values())
        out = {
            **base,
            "status": "pass" if ok else "fail",
            "checks": checks,
            "metrics": {
                "rows": len(rows),
                "duplicate_ratio": round(dup_ratio, 4),
            },
        }
        _write(Path(args.output_json), out)
        if ok:
            print("OK: canon insight minimum quality gate pass")
            return 0
        print("FAIL: canon insight minimum quality gate fail", file=sys.stderr)
        return 1
    except Exception as e:
        out = {
            **base,
            "status": "fail",
            "error": str(e),
            "checks": checks,
        }
        _write(Path(args.output_json), out)
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

