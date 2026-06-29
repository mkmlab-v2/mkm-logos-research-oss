#!/usr/bin/env python3
"""HG-6 lite — 300-anchor primitive / fundamental-force distribution (HYPO).

Does NOT modify gematria_bridge_v1 kernel or batch anchor files.

Reproducible:
  py scripts/build_logos_fundamental_force_primitive_report_v1.py
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1"
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1_manifest_latest.json"
LEXICON = ROOT / "docs/final/artifacts/logos_fundamental_force_lexicon_v1.json"
OUT = ROOT / "docs/final/artifacts/logos_fundamental_force_primitive_report_v1_latest.json"


def _vector_spread(v: dict[str, float]) -> float:
    vals = [float(v[k]) for k in ("S", "L", "K", "M")]
    return max(vals) - min(vals)


def _top_alignment(anchor: dict[str, Any]) -> dict[str, Any] | None:
    rows = anchor.get("kernel_alignment") or []
    if not rows:
        return None
    return max(rows, key=lambda r: float(r.get("similarity_adjusted", r.get("similarity", 0))))


def build_report(
    *,
    batch_dir: Path = BATCH_DIR,
    manifest_path: Path = MANIFEST,
    lexicon_path: Path = LEXICON,
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lexicon = json.loads(lexicon_path.read_text(encoding="utf-8"))
    primitive_to_force = {e["primitive"]: e for e in lexicon["entries"]}

    stems = sorted(manifest.get("paths", {}).keys())
    primitive_top1 = Counter()
    force_top1 = Counter()
    spreads: list[float] = []
    per_anchor: list[dict[str, Any]] = []

    for stem in stems:
        anchor = json.loads((batch_dir / f"{stem}.json").read_text(encoding="utf-8"))
        top = _top_alignment(anchor)
        spread = _vector_spread(anchor["vector_4d"])
        spreads.append(spread)
        if not top:
            continue
        primitive = str(top["primitive"])
        primitive_top1[primitive] += 1
        force_row = primitive_to_force.get(primitive)
        force_id = force_row["force_id"] if force_row else "unknown"
        force_top1[force_id] += 1
        per_anchor.append(
            {
                "file_stem": stem,
                "anchor_id": anchor.get("anchor_id"),
                "verse_refs": anchor.get("verse_refs") or [],
                "vector_4d": anchor.get("vector_4d"),
                "spread_4d": round(spread, 4),
                "top_primitive": primitive,
                "top_force_id": force_id,
                "top_similarity_adjusted": top.get("similarity_adjusted", top.get("similarity")),
                "force_copy_ko": (
                    f"[HYPO] {force_row['force_label_ko']} ↔ {force_row['sasang_label_ko']}"
                    if force_row
                    else None
                ),
            }
        )

    n = len(stems)
    harmony_share = primitive_top1.get("harmony", 0) / n if n else 0.0

    return {
        "schema": "logos_fundamental_force_primitive_report_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "materialize_batch": False,
        "kernel_recipe_id": "gematria_bridge_v1",
        "pedagogical_isomorphism_only": True,
        "lexicon_path": lexicon_path.relative_to(ROOT).as_posix(),
        "batch_dir": batch_dir.relative_to(ROOT).as_posix(),
        "anchor_count": n,
        "summary": {
            "primitive_top1_counts": dict(primitive_top1),
            "force_top1_counts": dict(force_top1),
            "harmony_top1_share": round(harmony_share, 4),
            "spread_4d_mean": round(statistics.mean(spreads), 4) if spreads else 0.0,
            "spread_4d_median": round(statistics.median(spreads), 4) if spreads else 0.0,
            "spread_4d_min": round(min(spreads), 4) if spreads else 0.0,
            "spread_4d_max": round(max(spreads), 4) if spreads else 0.0,
        },
        "per_anchor": per_anchor,
        "disclaimer_ko": lexicon.get("disclaimer_ko"),
        "reproducible_command": "py scripts/build_logos_fundamental_force_primitive_report_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=BATCH_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--lexicon", type=Path, default=LEXICON)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    report = build_report(
        batch_dir=args.batch_dir,
        manifest_path=args.manifest,
        lexicon_path=args.lexicon,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"  anchors={report['anchor_count']} harmony_top1_share={report['summary']['harmony_top1_share']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
