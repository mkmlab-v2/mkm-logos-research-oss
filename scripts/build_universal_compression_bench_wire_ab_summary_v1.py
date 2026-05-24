#!/usr/bin/env python3
"""Aggregate per-lane wire AB JSON into one B-track summary (no Golden/active writes)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports/constitution/btrack_pilot"
LANES = (
    ("finance", PILOT / "comp_universal_bench_matrix_wire_ab_finance_v1.json"),
    ("enterprise", PILOT / "comp_universal_bench_matrix_wire_ab_enterprise_v1.json"),
    ("ijeoma", PILOT / "comp_universal_bench_matrix_wire_ab_ijeoma_v1.json"),
    ("ijeoma_chunk", PILOT / "comp_universal_bench_matrix_wire_ab_ijeoma_chunk_v1.json"),
)
OUT = PILOT / "comp_universal_bench_matrix_wire_ab_summary_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    rows: list[dict] = []
    missing: list[str] = []
    for key, path in LANES:
        if not path.is_file():
            missing.append(key)
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        h = doc.get("headline") or {}
        d = doc.get("deltas_wire_vs_baseline") or {}
        gw = doc.get("graph_wire") or {}
        rows.append(
            {
                "lane_key": key,
                "lane_id": doc.get("lane_id"),
                "case_count": doc.get("case_count"),
                "bridge_boost_cases": gw.get("bridge_boost_cases"),
                "economy_saving_pct": h.get("economy_saving_pct"),
                "wire_saving_pct": h.get("wire_saving_pct"),
                "economy_jaccard": h.get("economy_jaccard"),
                "wire_jaccard": h.get("wire_jaccard"),
                "delta_saving_pp": d.get("global_token_saving_rate_pp"),
                "delta_jaccard_pp": d.get("avg_reconstruction_fidelity_jaccard_pp"),
                "artifact": str(path.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    summary = {
        "schema": "comp_universal_bench_matrix_wire_ab_summary_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "lane_count": len(rows),
        "missing_lanes": missing,
        "rows": rows,
        "pattern_note": (
            "Wire selective with graph influence: Jaccard tends up, saving tends down slightly. "
            "Not comparable to Golden 40 MS 47.5% headline."
        ),
        "do_not_promote": [
            "Blend lane KPIs into MS/HWPX or MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "Auto-promote to Track A / live trading",
        ],
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subset_script = ROOT / "scripts/summarize_universal_bench_matrix_wire_ab_subset_v1.py"
    if subset_script.is_file() and rows:
        import subprocess

        subprocess.run(
            [sys.executable, str(subset_script)],
            cwd=ROOT,
            check=False,
        )
    print(json.dumps({"wrote": OUT.name, "lanes": len(rows), "missing": missing}, ensure_ascii=False))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
