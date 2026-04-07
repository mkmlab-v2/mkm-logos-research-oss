#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "general_compression_eval_input_v1.json"
DEFAULT_SWEEP = ROOT / "docs" / "final" / "artifacts" / "general_compression_sweep_result_v1.json"
DEFAULT_TOLERANCE = ROOT / "docs" / "final" / "artifacts" / "general_compression_domain_tolerance_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_compression_90pct_failure_taxonomy_v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _domain_map(doc: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in doc.get("compression_cases", []):
        if isinstance(c, dict):
            out[str(c.get("id"))] = str(c.get("domain", "unknown"))
    return out


def _by_domain(report: dict[str, Any], id_to_domain: dict[str, str]) -> dict[str, dict[str, float]]:
    rows = (report.get("compression_metrics") or {}).get("cases") or []
    bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        cid = str(r.get("id", ""))
        bucket[id_to_domain.get(cid, "unknown")].append(r)
    out: dict[str, dict[str, float]] = {}
    for d, rs in bucket.items():
        if not rs:
            continue
        n = len(rs)
        out[d] = {
            "case_count": float(n),
            "avg_saving_rate": sum(float(x.get("token_saving_rate", 0.0)) for x in rs) / n,
            "avg_jaccard": sum(float(x.get("reconstruction_fidelity_jaccard", 0.0)) for x in rs) / n,
            "avg_sensitive_integrity": sum(float(x.get("sensitive_integrity", 0.0)) for x in rs) / n,
            "sensitive_violations": float(sum(1 for x in rs if bool(x.get("sensitive_violation")))),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Report 90pct-profile failure taxonomy for general compression.")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--sweep", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--tolerance", type=Path, default=DEFAULT_TOLERANCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _load(args.input)
    sweep = _load(args.sweep)
    tol = _load(args.tolerance)
    id_to_domain = _domain_map(doc)
    best = sweep.get("best_go_candidate") or sweep.get("best_candidate") or {}

    baseline = evaluate_report(
        doc,
        source_input=str(args.input),
        mode="baseline",
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
    )
    best_report = evaluate_report(
        doc,
        source_input=str(args.input),
        mode="experimental",
        strategy=str(best.get("strategy", "A")),
        intensity=str(best.get("intensity", "high")),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        general_max_saving_rate=float(best.get("general_max_saving_rate", 0.55)),
        sensitive_max_saving_rate=float(best.get("sensitive_max_saving_rate", 0.6)),
        hangul_max_saving_rate=float(best.get("hangul_max_saving_rate", 0.6)),
    )
    profile90 = evaluate_report(
        doc,
        source_input=str(args.input),
        mode="experimental",
        strategy="A",
        intensity="extreme",
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        general_max_saving_rate=0.9,
        sensitive_max_saving_rate=0.9,
        hangul_max_saving_rate=0.9,
    )

    base_d = _by_domain(baseline, id_to_domain)
    best_d = _by_domain(best_report, id_to_domain)
    p90_d = _by_domain(profile90, id_to_domain)

    tol_map = {str(x.get("domain")): x for x in (tol.get("domains") or []) if isinstance(x, dict)}
    failures: list[dict[str, Any]] = []
    for domain, metrics in p90_d.items():
        t = tol_map.get(domain, {})
        reasons: list[str] = []
        if float(metrics.get("avg_jaccard", 0.0)) < float(t.get("fidelity_floor", 0.6)):
            reasons.append("fidelity_below_domain_floor")
        if float(metrics.get("avg_sensitive_integrity", 0.0)) < float(t.get("sensitive_integrity_floor", 0.99)):
            reasons.append("sensitive_integrity_below_domain_floor")
        if float(metrics.get("sensitive_violations", 0.0)) > float(t.get("max_allowed_sensitive_violations", 0.0)):
            reasons.append("sensitive_violation_count_exceeded")
        if reasons:
            failures.append(
                {
                    "domain": domain,
                    "risk_mode": t.get("risk_mode", "unknown"),
                    "reasons": reasons,
                    "metrics": metrics,
                }
            )

    out = {
        "schema": "general_compression_90pct_failure_taxonomy_v1",
        "source_input": str(args.input.resolve()),
        "profiles": {
            "baseline": "mode=baseline",
            "best_go_profile": {
                "strategy": best.get("strategy"),
                "intensity": best.get("intensity"),
                "general_max_saving_rate": best.get("general_max_saving_rate"),
                "sensitive_max_saving_rate": best.get("sensitive_max_saving_rate"),
                "hangul_max_saving_rate": best.get("hangul_max_saving_rate"),
            },
            "strict_90_profile": {
                "strategy": "A",
                "intensity": "extreme",
                "general_max_saving_rate": 0.9,
                "sensitive_max_saving_rate": 0.9,
                "hangul_max_saving_rate": 0.9,
            },
        },
        "domain_summary": {
            "baseline": base_d,
            "best_go": best_d,
            "strict_90": p90_d,
        },
        "failure_taxonomy": failures,
        "decision_90pct_ready": "NO_GO" if failures else "GO",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "decision_90pct_ready": out["decision_90pct_ready"], "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
