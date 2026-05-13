#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate docs/final/schemas/logos_insight_bundle_v1.non_degraded.example.json from committed upstream fixtures.

Upstream JSON/JSONL lives under docs/final/artifacts/fixtures/logos_insight_bundle_non_degraded_upstream/
(same payloads as tests/test_build_logos_insight_bundle_v1._write_fixtures).

Usage (repo root):
  py scripts/materialize_logos_insight_bundle_non_degraded_example_v1.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_logos_insight_bundle_v1 import build_bundle  # noqa: E402

UPSTREAM = ROOT / "docs/final/artifacts/fixtures/logos_insight_bundle_non_degraded_upstream"
OUT = ROOT / "docs/final/schemas/logos_insight_bundle_v1.non_degraded.example.json"
FROZEN_UTC = "2026-05-14T00:00:00Z"


def main() -> int:
    m = UPSTREAM / "morphology_registry.json"
    s = UPSTREAM / "semantic_edge_quality.json"
    i = UPSTREAM / "insight_candidates.json"
    b = UPSTREAM / "bridge_edges.jsonl"
    r = UPSTREAM / "regime_shift.json"
    for p in (m, s, i, b, r):
        if not p.is_file():
            print(f"missing upstream fixture: {p}", file=sys.stderr)
            return 1

    bundle = build_bundle(
        morphology_path=m,
        semantic_path=s,
        insight_path=i,
        bridge_path=b,
        regime_path=r,
        top_k=4,
        citation_pack_limit=16,
    )
    if bundle.get("degraded"):
        print(f"unexpected degraded missing={bundle.get('missing_upstream')}", file=sys.stderr)
        return 1

    bundle["generated_at_utc"] = FROZEN_UTC
    note = str(bundle["audit"]["determinism_note"])
    tail = (
        f" | committed non_degraded example: generated_at_utc={FROZEN_UTC}; "
        "upstream: docs/final/artifacts/fixtures/logos_insight_bundle_non_degraded_upstream/"
    )
    bundle["audit"]["determinism_note"] = (note + tail)[:2000]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
