#!/usr/bin/env python3
"""[HYPO] Merge Golden-40 shard eval reports into one aggregate."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import _beat, _frozen_active


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_report(path: Path) -> dict[str, Any]:
    rep = path.with_suffix(".report.json")
    if rep.is_file():
        return json.loads(rep.read_text(encoding="utf-8-sig"))
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    ptr = doc.get("report_pointer")
    if ptr:
        rep2 = ROOT / str(ptr).replace("/", "\\")
        if rep2.is_file():
            return json.loads(rep2.read_text(encoding="utf-8-sig"))
    raise FileNotFoundError(f"missing report for {path}")


def _merge_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for rep in reports:
        cm = rep.get("compression_metrics") or {}
        rows.extend(cm.get("cases") or [])
    total_raw = 0
    total_saved = 0
    fid_sum = 0.0
    fid_n = 0
    min_fid = 1.0
    sens_viol = 0
    for r in rows:
        raw_t = int(r.get("raw_tokens") or r.get("raw_token_count") or 0)
        comp_t = int(r.get("compressed_tokens") or r.get("compressed_token_count") or 0)
        if raw_t <= 0:
            continue
        total_raw += raw_t
        total_saved += max(0, raw_t - comp_t)
        j = float(r.get("reconstruction_fidelity_jaccard") or 0)
        fid_sum += j
        fid_n += 1
        min_fid = min(min_fid, j)
        if r.get("sensitive_integrity_ok") is False or float(
            r.get("sensitive_integrity") or 1.0
        ) < 1.0:
            sens_viol += 1
    saving = (total_saved / total_raw) if total_raw else 0.0
    avg_j = (fid_sum / fid_n) if fid_n else 0.0
    return {
        "case_count": fid_n,
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": avg_j,
        "min_reconstruction_fidelity_jaccard": min_fid if fid_n else 0.0,
        "sensitive_violation_count": sens_viol,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("shard_jsons", nargs="+", type=Path)
    ap.add_argument(
        "--out-json",
        type=Path,
        default=ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_golden40_merged_v1_latest.json",
    )
    args = ap.parse_args()

    meta: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for p in args.shard_jsons:
        doc = json.loads(p.read_text(encoding="utf-8-sig"))
        meta.append(doc)
        reports.append(_load_report(p))

    merged = _merge_reports(reports)
    frozen = _frozen_active()
    beat = _beat(merged, frozen)

    out = {
        "schema": "nextgen_ng40_golden40_merged_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "shard_sources": [str(p) for p in args.shard_jsons],
        "shards": meta,
        "aggregate": merged,
        "beat_check": beat,
        "golden40_compatible": True,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "case_count": merged.get("case_count"),
                "beat_frozen": beat.get("beat_frozen"),
                "saving": merged.get("global_token_saving_rate"),
                "jaccard": merged.get("avg_reconstruction_fidelity_jaccard"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
