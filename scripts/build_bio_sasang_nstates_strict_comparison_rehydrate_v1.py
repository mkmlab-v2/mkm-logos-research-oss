#!/usr/bin/env python3
"""
Re-materialize reports/bio_sasang_nstates_strict_comparison_v2.json when the
original FireProt-backed computation artifacts are missing from disk.

This does NOT re-run FireProt / DDG statistics. It writes a deterministic JSON
artifact with provenance.mode=rehydrated_from_ssot_documentation so Fact-Lock
readers can distinguish it from a fresh bench recompute.

Source row (numbers + protocol): docs/final/CENTRAL_AGENT_MEMORY_V1.md
\"2026-04-20 (Bio Sasang n-state strict)\" table line as of 2026-05-04.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "bio_sasang_nstates_strict_comparison_v2.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_payload() -> dict:
    # Spearman summary metric (rank correlation strength) from CENTRAL row.
    by_n = {
        "8": {"spearman": 0.4958, "rank": 4},
        "10": {"spearman": 0.5028, "rank": 3},
        "12": {"spearman": 0.5295, "rank": 1},
        "14": {"spearman": 0.5175, "rank": 2},
    }
    ranking = sorted(by_n.keys(), key=lambda k: float(by_n[k]["spearman"]), reverse=True)
    return {
        "schema": "bio_sasang_nstates_strict_comparison_v2",
        "version": 2,
        "regeneration": {
            "mode": "rehydrated_from_ssot_documentation",
            "source_document": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
            "source_anchor": "2026-04-20 (Bio Sasang n-state strict)",
            "regenerated_at_utc": _utc_now(),
            "warning": (
                "Not a fresh FireProt/DDG recomputation: cohort files and original "
                "runner are absent from this workspace. Numbers mirror CENTRAL row "
                "until a reproducible pipeline is restored."
            ),
        },
        "cohort": {
            "name": "FireProtDB DDG strict",
            "n_rows": 4783,
        },
        "protocol": {
            "n_states_candidates": [8, 10, 12, 14],
            "family_folds": 5,
            "seeds": [42, 43, 44],
            "bootstrap_samples": 5000,
        },
        "results": {
            "metric": "spearman",
            "by_n_states": by_n,
            "ranking_by_spearman_desc": ranking,
            "recommended_n_states": 12,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output JSON (default: {DEFAULT_OUT})",
    )
    args = ap.parse_args()
    out: Path = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
