#!/usr/bin/env python3
"""Build lens_multi_axis_audit_envelope_v1 from independent lens artifacts (B-track PoC)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lens_multi_axis_audit_v1 import build_envelope_from_lens_paths

DEFAULT_MYEONGNI = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
DEFAULT_SASANG = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
DEFAULT_INTERPRET = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/lens_multi_axis_audit_envelope_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build multi-axis audit envelope (no GraphRAG).")
    ap.add_argument("--myeongni-lens", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--sasang-lens", type=Path, default=DEFAULT_SASANG)
    ap.add_argument(
        "--interpret-status",
        type=Path,
        default=DEFAULT_INTERPRET,
        help="Optional interpret harness status JSON (pointer only).",
    )
    ap.add_argument("--no-interpret", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fail-on-lint", action="store_true", help="Exit 1 if forbidden substring lint fails.")
    args = ap.parse_args()

    interpret = None if args.no_interpret else args.interpret_status
    env = build_envelope_from_lens_paths(args.myeongni_lens, args.sasang_lens, interpret_path=interpret)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"lint_pass={env['lint']['pass']}")
    if args.fail_on_lint and not env["lint"]["pass"]:
        print(f"lint_hits={env['lint']['forbidden_substring_hits']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
