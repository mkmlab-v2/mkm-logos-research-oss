#!/usr/bin/env python3
"""Gate PersonaDiary Android design tokens SSOT + globals.css alignment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from personadiary_android_design_tokens_v1 import (  # noqa: E402
    DEFAULT_CSS,
    DEFAULT_SSOT,
    SCHEMA_PATH,
    load_ssot,
    validate_ssot,
)

DEFAULT_OUT = ROOT / "reports/personadiary_android_design_tokens_gate_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssot-json", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--css", type=Path, default=DEFAULT_CSS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    errors: list[str] = []
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    doc = load_ssot(args.ssot_json)
    try:
        jsonschema.validate(instance=doc, schema=schema)
    except jsonschema.ValidationError as exc:
        errors.append(f"schema:{exc.message}")

    errors.extend(validate_ssot(doc, css_path=args.css))

    ok = len(errors) == 0
    report = {
        "schema": "personadiary_android_design_tokens_gate_v1",
        "ok": ok,
        "ssot_json": str(args.ssot_json.relative_to(ROOT)),
        "css_ssot": str(args.css.relative_to(ROOT)),
        "smoke_markers": doc.get("smoke_markers") or [],
        "touch_target_min_px": (doc.get("m3_inspired") or {}).get("touch_target_min_px"),
        "errors": errors,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
