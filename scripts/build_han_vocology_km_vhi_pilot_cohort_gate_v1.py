#!/usr/bin/env python3
"""Build KM-VHI pilot cohort improvement gate report (B-track · M11)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"
PROTOCOL = ROOT / "docs/final/artifacts/han_vocology_km_vhi_validation_pilot_v1_latest.json"
OUT = ROOT / "reports/han_vocology_km_vhi_pilot_cohort_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _band(delta: float, *, excellent: float, partial_min: float, non_responder_max: float) -> str:
    if delta >= excellent:
        return "excellent"
    if delta >= partial_min:
        return "partial"
    if delta <= non_responder_max:
        return "non_responder"
    return "between_partial_non_responder"


def build_gate(path: Path, *, protocol: dict[str, Any]) -> dict[str, Any]:
    bands = protocol.get("improvement_bands") or {}
    excellent = float(bands.get("excellent_pct", 20))
    partial_min = float(bands.get("partial_pct_min", 10))
    non_responder_max = float(bands.get("non_responder_pct_max", 10))

    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))

    by_patient: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        pid = str(r.get("pseudonym_id") or "")
        by_patient.setdefault(pid, []).append(r)

    cohorts: list[dict[str, Any]] = []
    band_counts: dict[str, int] = {"excellent": 0, "partial": 0, "non_responder": 0, "between_partial_non_responder": 0}

    for pid, visits in sorted(by_patient.items()):
        meta = visits[0]
        w8 = next((v for v in visits if v.get("visit_week") == 8), None)
        w12 = next((v for v in visits if v.get("visit_week") == 12), None)
        delta_w8 = w8.get("delta_pct_vs_week0") if w8 else None
        delta_w12 = w12.get("delta_pct_vs_week0") if w12 else None

        band_w8 = None
        if delta_w8 is not None:
            band_w8 = _band(
                float(delta_w8),
                excellent=excellent,
                partial_min=partial_min,
                non_responder_max=non_responder_max,
            )
            band_counts[band_w8] = band_counts.get(band_w8, 0) + 1

        cohorts.append(
            {
                "pseudonym_id": pid,
                "site_id": meta.get("site_id"),
                "cb_id": meta.get("cb_id"),
                "clinical_policy": meta.get("clinical_policy"),
                "delta_pct_week8": delta_w8,
                "delta_pct_week12": delta_w12,
                "band_week8": band_w8,
                "visit_weeks": sorted(
                    int(v["visit_week"]) if v.get("visit_week") is not None else -1 for v in visits
                ),
            }
        )

    with_w8 = [c for c in cohorts if c["delta_pct_week8"] is not None]
    excellent_n = sum(1 for c in with_w8 if c["band_week8"] == "excellent")
    ok = bool(with_w8) and excellent_n == len(with_w8)

    return {
        "schema": "han_vocology_km_vhi_pilot_cohort_gate_v1",
        "ok": ok,
        "track": "B",
        "send_gate": "HOLD",
        "cohort_count": len(cohorts),
        "cohorts_with_week8": len(with_w8),
        "excellent_at_week8": excellent_n,
        "improvement_bands": bands,
        "band_counts_week8": band_counts,
        "cohorts": cohorts,
        "note": "HYPO education gate only — not clinical efficacy claim",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--protocol", type=Path, default=PROTOCOL)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": "jsonl_missing"}, ensure_ascii=False))
        return 1

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    result = build_gate(args.jsonl, protocol=protocol)
    result["generated_at_utc"] = _utc()
    result["jsonl"] = str(args.jsonl)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": result["ok"],
                "excellent_at_week8": result["excellent_at_week8"],
                "cohorts_with_week8": result["cohorts_with_week8"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
