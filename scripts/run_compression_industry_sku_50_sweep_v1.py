#!/usr/bin/env python3
"""[HYPO] Industry SKU PoC — rebuild corpora at 50 rows/SKU and summarize vs 30-row baseline."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_DEFAULT = ROOT / "reports/compression_industry_sku_50_sweep_v1_latest.json"
BASELINE_BUNDLE = ROOT / "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json"
SCHEMA = "compression_industry_sku_50_sweep_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows-per-sku", type=int, default=50)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args(argv)

    rows = max(1, args.rows_per_sku)
    summary_path = ROOT / f"reports/compression_b2b_sku_industry_poc_bundle_{rows}_v1_latest.json"

    steps: list[dict[str, Any]] = []

    for script, extra in [
        ("build_compression_b2b_industry_poc_corpus_v1.py", ["--rows-per-sku", str(rows)]),
        (
            "run_compression_b2b_sku_industry_poc_bundle_v1.py",
            [
                "--skip-build",
                "--rows-per-sku",
                str(rows),
                "--out-summary",
                str(summary_path.relative_to(ROOT)).replace("\\", "/"),
            ],
        ),
    ]:
        proc = subprocess.run([PY, str(ROOT / "scripts" / script), *extra], cwd=str(ROOT), capture_output=True, text=True)
        steps.append(
            {
                "script": script,
                "exit_code": proc.returncode,
                "output_tail": (proc.stdout or proc.stderr or "").strip().splitlines()[-4:],
            }
        )
        if proc.returncode != 0:
            break

    bundle = _load(summary_path) if summary_path.is_file() else {}
    baseline = _load(BASELINE_BUNDLE) if BASELINE_BUNDLE.is_file() else {}
    baseline_by_sku = {
        s.get("external_sku"): s
        for s in (baseline.get("steps") or [])
        if s.get("external_sku")
    }

    comparisons: list[dict[str, Any]] = []
    for step in bundle.get("steps") or []:
        sku = step.get("external_sku")
        base = baseline_by_sku.get(sku) or {}
        rate = step.get("mean_token_saving_rate_proxy")
        base_rate = base.get("mean_token_saving_rate_proxy")
        delta_pp = None
        if isinstance(rate, (int, float)) and isinstance(base_rate, (int, float)):
            delta_pp = round((float(rate) - float(base_rate)) * 100, 2)
        comparisons.append(
            {
                "external_sku": sku,
                "case_count": step.get("case_count"),
                "raw_saving_pct": round(float(rate) * 100, 2) if isinstance(rate, (int, float)) else None,
                "mean_jaccard_proxy": step.get("mean_jaccard_proxy"),
                "baseline_30_saving_pct": round(float(base_rate) * 100, 2) if isinstance(base_rate, (int, float)) else None,
                "delta_pp_vs_30_row_baseline": delta_pp,
            }
        )

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "rows_per_sku": rows,
        "bundle_summary_path": str(summary_path.relative_to(ROOT)).replace("\\", "/"),
        "baseline_bundle_path": str(BASELINE_BUNDLE.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
        "sku_comparisons": comparisons,
        "chain_ok": all(s.get("exit_code") == 0 for s in steps) and bool(comparisons),
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    for c in comparisons:
        print(
            f"  {c['external_sku']}: {c['raw_saving_pct']}% "
            f"(Δ vs30={c.get('delta_pp_vs_30_row_baseline')})"
        )
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
