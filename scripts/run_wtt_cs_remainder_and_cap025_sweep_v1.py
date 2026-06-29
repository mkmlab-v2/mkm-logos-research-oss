#!/usr/bin/env python3
"""WTT premium CS — cap 0.25/0.20 full-corpus replay + multi-turn remainder (000·017) grid [HYPO]."""

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
DEFAULT_CORPUS = ROOT / "data/compression/stateless_poc_prospect_wtt-premium-cs-customer-v1_v1.jsonl"
DEFAULT_OVERLAY = ROOT / "docs/final/artifacts/tenant_wtt-premium-cs-customer-v1_must_keep_overlay_v1.json"
DEFAULT_OUT = ROOT / "reports/wtt_cs_remainder_and_cap025_sweep_v1_latest.json"
REMAINDER_IDS = {
    "prospect-wtt-premium-cs-customer-v1-000",
    "prospect-wtt-premium-cs-customer-v1-017",
}

FULL_CORPUS_ARMS: list[dict[str, Any]] = [
    {"arm_id": "economy_shortcap_30_025", "profile": "economy", "threshold": 30, "max_saving": 0.25},
    {"arm_id": "economy_shortcap_30_020", "profile": "economy", "threshold": 30, "max_saving": 0.20},
    {"arm_id": "fidelity_shortcap_30_025", "profile": "fidelity", "threshold": 30, "max_saving": 0.25},
    {"arm_id": "fidelity_shortcap_30_030", "profile": "fidelity", "threshold": 30, "max_saving": 0.30},
]

REMAINDER_ARMS: list[dict[str, Any]] = []
for profile in ("economy", "fidelity"):
    for threshold in (30, 35, 45, 50):
        for max_saving in (0.15, 0.20, 0.25, 0.30):
            REMAINDER_ARMS.append(
                {
                    "arm_id": f"{profile}_t{threshold}_cap{int(max_saving * 100):03d}",
                    "profile": profile,
                    "threshold": threshold,
                    "max_saving": max_saving,
                }
            )


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_subset_corpus(source: Path, dest: Path, ids: set[str]) -> int:
    rows: list[str] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("id") in ids:
            rows.append(json.dumps(obj, ensure_ascii=False))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(rows)


def _run_poc(
    *,
    corpus: Path,
    overlay: Path,
    arm_id: str,
    profile: str,
    threshold: int,
    max_saving: float,
    max_cases: int,
    report_rel: str,
) -> tuple[int, dict[str, Any]]:
    cmd = [
        PY,
        "scripts/run_customer_compression_stateless_poc_v1.py",
        "--input-jsonl",
        corpus.relative_to(ROOT).as_posix(),
        "--sku",
        "MKM-CHAT-D1",
        "--compression-profile",
        profile,
        "--max-cases",
        str(max_cases),
        "--must-keep-overlay-json",
        overlay.relative_to(ROOT).as_posix(),
        "--out-json",
        report_rel,
        "--relax-pass-gate",
        "--short-context-token-threshold",
        str(threshold),
        "--short-context-max-saving-rate",
        str(max_saving),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    report_path = ROOT / report_rel
    summary: dict[str, Any] = {"exit_code": proc.returncode, "report_path": report_rel}
    if report_path.is_file():
        doc = json.loads(report_path.read_text(encoding="utf-8-sig"))
        agg = doc.get("aggregate") or {}
        cc = int(doc.get("case_count") or 0)
        cp = int(doc.get("cases_passed") or 0)
        summary.update(
            {
                "case_count": cc,
                "cases_passed": cp,
                "pass_rate": round(cp / cc, 4) if cc else 0.0,
                "mean_saving_all": round(float(agg.get("mean_token_saving_rate_proxy_all_cases") or 0.0), 6),
                "mean_jaccard_all": round(float(agg.get("mean_jaccard_proxy_all_cases") or 0.0), 6),
                "per_case": doc.get("cases") or doc.get("per_case") or [],
            }
        )
    return proc.returncode, summary


def _per_id_pass(per_case: list[dict[str, Any]], case_id: str) -> dict[str, Any] | None:
    for row in per_case:
        if row.get("id") == case_id:
            return {
                "id": case_id,
                "ok": row.get("ok"),
                "jaccard_proxy": row.get("jaccard_proxy"),
                "token_saving_rate_proxy": row.get("token_saving_rate_proxy"),
            }
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-jsonl", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--overlay-json", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    corpus = args.corpus_jsonl.resolve()
    overlay = args.overlay_json.resolve()
    if not corpus.is_file():
        print(f"error: missing corpus: {corpus}", file=sys.stderr)
        return 2

    subset = corpus.parent / f"{corpus.stem}_remainder_000_017_v1.jsonl"
    n_sub = _build_subset_corpus(corpus, subset, REMAINDER_IDS)
    if n_sub != 2:
        print(f"error: expected 2 remainder rows, got {n_sub}", file=sys.stderr)
        return 2

    chain_ok = True
    full_rows: list[dict[str, Any]] = []
    for arm in FULL_CORPUS_ARMS:
        report_rel = f"reports/wtt_cap025_full_{arm['arm_id']}_v1_latest.json"
        rc, summary = _run_poc(
            corpus=corpus,
            overlay=overlay,
            arm_id=arm["arm_id"],
            profile=arm["profile"],
            threshold=arm["threshold"],
            max_saving=arm["max_saving"],
            max_cases=30,
            report_rel=report_rel,
        )
        full_rows.append({**arm, **summary})
        if rc != 0:
            chain_ok = False

    remainder_rows: list[dict[str, Any]] = []
    for arm in REMAINDER_ARMS:
        report_rel = f"reports/wtt_remainder_{arm['arm_id']}_v1_latest.json"
        rc, summary = _run_poc(
            corpus=subset,
            overlay=overlay,
            arm_id=arm["arm_id"],
            profile=arm["profile"],
            threshold=arm["threshold"],
            max_saving=arm["max_saving"],
            max_cases=2,
            report_rel=report_rel,
        )
        per_case = summary.pop("per_case", [])
        id_pass = {
            cid: _per_id_pass(per_case, cid) for cid in sorted(REMAINDER_IDS)
        }
        both_pass = all((id_pass.get(cid) or {}).get("ok") is True for cid in REMAINDER_IDS)
        remainder_rows.append({**arm, **summary, "per_id": id_pass, "both_pass": both_pass})
        if rc != 0:
            chain_ok = False

    best_full = max(full_rows, key=lambda r: (r.get("cases_passed") or 0, r.get("mean_jaccard_all") or 0.0))
    passing_remainder = [r for r in remainder_rows if r.get("both_pass")]
    best_remainder = None
    if passing_remainder:
        best_remainder = max(
            passing_remainder,
            key=lambda r: (
                sum(
                    (r.get("per_id", {}).get(cid) or {}).get("jaccard_proxy") or 0.0
                    for cid in REMAINDER_IDS
                ),
                -(r.get("max_saving") or 0.0),
            ),
        )

    doc = {
        "schema": "wtt_cs_remainder_and_cap025_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_promotion": False,
        "remainder_ids": sorted(REMAINDER_IDS),
        "subset_corpus": subset.relative_to(ROOT).as_posix(),
        "chain_ok": chain_ok,
        "full_corpus_30": {
            "arms": full_rows,
            "best_arm": best_full.get("arm_id"),
            "best_cases_passed": best_full.get("cases_passed"),
            "best_pass_rate": best_full.get("pass_rate"),
        },
        "remainder_grid": {
            "arm_count": len(remainder_rows),
            "arms_both_pass_count": len(passing_remainder),
            "best_both_pass_arm": (best_remainder or {}).get("arm_id"),
            "best_both_pass": best_remainder,
            "sample_top5_by_jaccard_sum": sorted(
                remainder_rows,
                key=lambda r: sum(
                    (r.get("per_id", {}).get(cid) or {}).get("jaccard_proxy") or 0.0
                    for cid in REMAINDER_IDS
                ),
                reverse=True,
            )[:5],
        },
        "conclusion_ko": (
            f"full30 best={best_full.get('arm_id')} pass={best_full.get('cases_passed')}/30; "
            f"remainder both_pass arms={len(passing_remainder)}/{len(remainder_rows)}. "
            "Track A·SEND 승격 아님."
        ),
    }
    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(
        json.dumps(
            {
                "chain_ok": chain_ok,
                "full_best": best_full.get("arm_id"),
                "full_pass": best_full.get("cases_passed"),
                "remainder_both_pass": len(passing_remainder),
            },
            ensure_ascii=False,
        )
    )
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
