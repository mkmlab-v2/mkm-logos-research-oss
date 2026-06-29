#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI: resolve integrated_wellness_solution_v2 seed → resolved JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrated_wellness_solution_v2_core import (  # noqa: E402
    ROOT as _ROOT,
    load_json,
    resolve_integrated_wellness,
    validate_against_schema,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve IWS v2 Tier 0–3")
    parser.add_argument("--in-json", required=True, type=Path, help="Seed SSOT JSON")
    parser.add_argument("--out-json", required=True, type=Path, help="Resolved output")
    parser.add_argument(
        "--lexicon-json",
        type=Path,
        default=_ROOT / "docs" / "final" / "artifacts" / "a_code_wellness_archetype_lexicon_v1.json",
    )
    parser.add_argument("--validate", action="store_true", help="jsonschema validate output")
    args = parser.parse_args()

    seed = load_json(args.in_json)
    resolved = resolve_integrated_wellness(seed, lexicon_path=args.lexicon_json)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(resolved, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.validate:
        validate_against_schema(resolved)

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "resolved_count": len(resolved.get("resolved_evidence_stream", [])),
                "suppressed_count": len(resolved.get("suppression_log", [])),
                "a_code": resolved.get("client_profile", {}).get("a_code_consumer"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
