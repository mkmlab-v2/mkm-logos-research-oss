#!/usr/bin/env python3
"""Tier-1 corpus expansion pilot — motif distribution report only (no batch merge).

Reproducible:
  py scripts/run_logos_corpus_expansion_pilot_v1.py

Output:
  docs/final/artifacts/logos_corpus_expansion_pilot_v1_latest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.logos_corpus_expansion_scan_v1 import scan_tier1_corpus

DEFAULT_CORPUS = ROOT / "data" / "logos" / "verse_4pipeline_full_31102.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
SIDECAR = ROOT / "data/logos/sidecar_apocrypha_dss_hypo_v1.jsonl"
OUT = ROOT / "docs/final/artifacts/logos_corpus_expansion_pilot_v1_latest.json"


def _sidecar_stats(path: Path = SIDECAR) -> dict[str, int | str]:
    tier2 = tier3 = 0
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            tier = str(row.get("tier") or "")
            if tier == "tier2_apocrypha":
                tier2 += 1
            elif tier == "tier3_dss":
                tier3 += 1
    total = tier2 + tier3
    if total == 0:
        status = "container_ready"
    elif tier2 >= 1 and tier3 >= 1:
        status = "pilot_seeded"
    else:
        status = "partial"
    return {
        "row_count": total,
        "tier2_apocrypha_count": tier2,
        "tier3_dss_count": tier3,
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    if not args.registry.is_file():
        print(f"Missing registry: {args.registry}", file=sys.stderr)
        return 2

    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scan = scan_tier1_corpus(corpus_path=args.corpus, registry_path=args.registry)

    doc = {
        "schema": "logos_corpus_expansion_pilot_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "materialize_batch": False,
        "tier1_scan": scan,
        "tier2_apocrypha_sidecar": {
            "path": "data/logos/sidecar_apocrypha_dss_hypo_v1.jsonl",
            "hypothesis_class": "HYPO",
            **{
                k: v
                for k, v in _sidecar_stats().items()
                if k in ("row_count", "tier2_apocrypha_count", "tier3_dss_count", "status")
            },
        },
        "tier3_dss_note_ko": "사해사본 인용 시 1QS·4Q258 등 사본 번호 병기 (LOGOS_NOTEBOOK_META_GUIDE)",
        "reproducible_command": "py scripts/run_logos_corpus_expansion_pilot_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"  verses={scan['verse_count']} motif_hits={scan['motif_hit_event_total']}")
    print(f"  skew_top={scan['skew_warning']['top_motif_stem']} share={scan['skew_warning']['top_motif_share_of_hits']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
