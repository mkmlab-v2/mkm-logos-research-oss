#!/usr/bin/env python3
"""Compare expansion dry-runs: 41658 base vs 3a overlay lexicon (research)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DRYRUN = ROOT / "scripts/run_golden40_expansion_dryrun_v1.py"
LEX_658 = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
LEX_3A = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_3a_pilot_overlay.json"
OUT_658 = ROOT / "reports/golden_40_expansion_dryrun_41658_lexicon_v1_latest.json"
OUT_3A = ROOT / "reports/golden_40_expansion_dryrun_3a_lexicon_v1_latest.json"
COMPARE_OUT = ROOT / "reports/golden_40_expansion_lexicon_ab_compare_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tier_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tier in doc.get("tiers") or []:
        agg = tier.get("aggregate_metrics") or {}
        rows.append(
            {
                "target": tier.get("target_case_count"),
                "saving": agg.get("global_token_saving_rate"),
                "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
                "floor_ok": tier.get("floor_regression_ok"),
                "golden_core_jaccard": (tier.get("golden_core_only_metrics") or {}).get(
                    "avg_reconstruction_fidelity_jaccard"
                ),
            }
        )
    return rows


def _run(lexicon: Path, out_json: Path, targets: str) -> int:
    if out_json.is_file():
        return 0
    cmd = [
        sys.executable,
        str(DRYRUN),
        "--pool-mode",
        "mixed_matrix",
        "--target-counts",
        targets,
        "--lexicon",
        str(lexicon),
        "--out-json",
        str(out_json),
    ]
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
    targets = "40,80,120"
    ec_658 = _run(LEX_658, OUT_658, targets)
    ec_3a = _run(LEX_3A, OUT_3A, targets) if not OUT_3A.is_file() else 0

    docs: dict[str, Any] = {}
    for label, path, ec in (
        ("lexicon_41658", OUT_658, ec_658),
        ("lexicon_3a_overlay", OUT_3A, ec_3a),
    ):
        if path.is_file():
            d = json.loads(path.read_text(encoding="utf-8"))
            docs[label] = {
                "artifact": str(path.relative_to(ROOT)).replace("\\", "/"),
                "exit_code": ec,
                "tier_summary": _tier_rows(d),
                "summary": d.get("summary"),
            }

    compare = {
        "schema": "golden_40_expansion_lexicon_ab_compare_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "promotion_recommendation": "HOLD",
        "would_change_active": False,
        "lexicons": docs,
        "finding_n40": (
            "At N=40, 3a overlay matches 41775 frozen KPI; 41658 base stays ~0.873."
            if docs.get("lexicon_3a_overlay") and docs.get("lexicon_41658")
            else "see tier_summary"
        ),
    }
    COMPARE_OUT.write_text(json.dumps(compare, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {COMPARE_OUT}")
    worst = max(ec_658, ec_3a)
    return 0 if worst == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
