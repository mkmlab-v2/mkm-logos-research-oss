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
    ap = argparse.ArgumentParser(description="Validate insight explainability sidecar.")
    ap.add_argument(
        "--input-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_explainability_v1.json",
    )
    ap.add_argument("--min-rows", type=int, default=5)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_explainability_quality_gate_v1.json",
    )
    args = ap.parse_args()

    checks = {"schema_ok": False, "rows_ok": False, "components_ok": False, "text_ok": False}
    base = {
        "schema": "original_corpus_regime_singularity_canon_insight_explainability_quality_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {"input_json": str(args.input_json), "min_rows": int(args.min_rows)},
    }
    try:
        data = _read_json(Path(args.input_json))
        checks["schema_ok"] = data.get("schema") == "original_corpus_regime_singularity_canon_insight_explainability_v1"
        rows = list(data.get("rows") or [])
        checks["rows_ok"] = len(rows) >= int(args.min_rows)
        checks["components_ok"] = bool(rows) and all((r.get("components") or {}).get("score_component") is not None for r in rows)
        checks["text_ok"] = bool(rows) and all(len(str(r.get("explanation_text") or "").strip()) >= 10 for r in rows)
        ok = all(checks.values())
        out = {**base, "status": "pass" if ok else "fail", "checks": checks, "metrics": {"rows": len(rows)}}
        _write(Path(args.output_json), out)
        if ok:
            print("OK: insight explainability quality gate pass")
            return 0
        print("FAIL: insight explainability quality gate fail", file=sys.stderr)
        return 1
    except Exception as e:
        _write(Path(args.output_json), {**base, "status": "fail", "error": str(e), "checks": checks})
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

