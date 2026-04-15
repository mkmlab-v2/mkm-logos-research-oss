# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.2}
# Balance: 90
# Purpose: Build Track A domain breakdown and low-fidelity case report.
# Keywords: compression, track_a, kpi, domain, analysis
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_domain_breakdown_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--active-report", type=Path, default=DEFAULT_ACTIVE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--top-n", type=int, default=10)
    args = ap.parse_args()

    active_path = args.active_report if args.active_report.is_absolute() else ROOT / args.active_report
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = json.loads(active_path.read_text(encoding="utf-8"))
    metrics = report.get("compression_metrics", {})
    cases: list[dict[str, Any]] = metrics.get("cases", [])

    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cases:
        route = row.get("route", {}) or {}
        domain = str(route.get("domain") or "unknown")
        by_domain[domain].append(row)

    domain_summary: list[dict[str, Any]] = []
    for domain, rows in sorted(by_domain.items(), key=lambda item: item[0]):
        count = len(rows)
        avg_save = sum(_safe_float(r.get("token_saving_rate")) for r in rows) / count
        avg_jaccard = sum(_safe_float(r.get("reconstruction_fidelity_jaccard")) for r in rows) / count
        min_jaccard = min(_safe_float(r.get("reconstruction_fidelity_jaccard")) for r in rows)
        domain_summary.append(
            {
                "domain": domain,
                "case_count": count,
                "avg_token_saving_rate": avg_save,
                "avg_reconstruction_fidelity_jaccard": avg_jaccard,
                "min_reconstruction_fidelity_jaccard": min_jaccard,
            }
        )

    low_fidelity_cases = sorted(
        [
            {
                "id": str(r.get("id") or ""),
                "domain": str((r.get("route") or {}).get("domain") or "unknown"),
                "token_saving_rate": _safe_float(r.get("token_saving_rate")),
                "reconstruction_fidelity_jaccard": _safe_float(r.get("reconstruction_fidelity_jaccard")),
                "raw_tokens": int(_safe_float(r.get("raw_tokens"))),
                "compressed_tokens": int(_safe_float(r.get("compressed_tokens"))),
            }
            for r in cases
        ],
        key=lambda item: item["reconstruction_fidelity_jaccard"],
    )[: max(1, args.top_n)]

    out_doc = {
        "schema": "track_a_domain_breakdown_v1",
        "generated_at_utc": _utc_now(),
        "input": str(active_path),
        "summary": {
            "case_count": int(metrics.get("case_count", len(cases))),
            "global_token_saving_rate": _safe_float(metrics.get("global_token_saving_rate")),
            "avg_reconstruction_fidelity_jaccard": _safe_float(metrics.get("avg_reconstruction_fidelity_jaccard")),
            "avg_sensitive_integrity": _safe_float(metrics.get("avg_sensitive_integrity")),
            "sensitive_violation_count": int(metrics.get("sensitive_violation_count", 0)),
        },
        "domain_breakdown": sorted(
            domain_summary,
            key=lambda item: item["avg_reconstruction_fidelity_jaccard"],
        ),
        "top_low_fidelity_cases": low_fidelity_cases,
    }

    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "domains": len(domain_summary),
                "worst_case": low_fidelity_cases[0] if low_fidelity_cases else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
