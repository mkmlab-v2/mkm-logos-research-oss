#!/usr/bin/env python3
"""Aggregate golden16 + combined32 shallow cost profiles for Phase 11-T deep bench [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/ollama_shallow_cost_deep_bench_v1_latest.json"
GOLDEN_GAP = ROOT / "reports/ollama_shallow_routing_oracle_gap_golden16_v1_latest.json"
STRESS_GAP = ROOT / "reports/ollama_shallow_oracle_gap_stress_v1_latest.json"
DEFAULT_THRESHOLDS = {
    "min_cloud_skip_ratio": 0.95,
    "min_deep_routing_recall": 0.95,
    "max_routing_oracle_gap": 0.0,
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _profile_from_gap(doc: dict[str, Any], *, label: str) -> dict[str, Any]:
    raw = doc.get("raw") or {}
    repair = doc.get("repair_v2") or raw
    return {
        "label": label,
        "report": doc.get("_source_path"),
        "bench_mode": doc.get("bench_mode"),
        "fixtures_evaluated": doc.get("fixtures_evaluated"),
        "raw": {
            "router_hit_rate": raw.get("router_hit_rate"),
            "routing_oracle_gap": raw.get("routing_oracle_gap"),
            "cloud_skip_ratio": raw.get("cloud_skip_ratio"),
            "deep_routing_recall": raw.get("deep_routing_recall"),
            "rows": raw.get("rows"),
        },
        "repair_v2": {
            "router_hit_rate": repair.get("router_hit_rate"),
            "routing_oracle_gap": repair.get("routing_oracle_gap"),
            "cloud_skip_ratio": repair.get("cloud_skip_ratio"),
            "deep_routing_recall": repair.get("deep_routing_recall"),
            "rows": repair.get("rows"),
            "note": repair.get("note") or "No repair layer; metrics equal raw.",
        },
    }


def _passes_thresholds(raw: dict[str, Any], thr: dict[str, float]) -> tuple[bool, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    skip = raw.get("cloud_skip_ratio")
    if thr.get("min_cloud_skip_ratio") is not None:
        checks.append(
            {
                "name": "min_cloud_skip_ratio",
                "ok": skip is not None and float(skip) >= float(thr["min_cloud_skip_ratio"]),
                "observed": skip,
                "threshold": thr["min_cloud_skip_ratio"],
            }
        )
    recall = raw.get("deep_routing_recall")
    if thr.get("min_deep_routing_recall") is not None:
        checks.append(
            {
                "name": "min_deep_routing_recall",
                "ok": recall is not None and float(recall) >= float(thr["min_deep_routing_recall"]),
                "observed": recall,
                "threshold": thr["min_deep_routing_recall"],
            }
        )
    gap = raw.get("routing_oracle_gap")
    if thr.get("max_routing_oracle_gap") is not None:
        checks.append(
            {
                "name": "max_routing_oracle_gap",
                "ok": gap is not None and float(gap) <= float(thr["max_routing_oracle_gap"]),
                "observed": gap,
                "threshold": thr["max_routing_oracle_gap"],
            }
        )
    ok = all(c["ok"] for c in checks) if checks else False
    return ok, checks


def build_deep_bench(
    *,
    golden_gap_path: Path = GOLDEN_GAP,
    stress_gap_path: Path = STRESS_GAP,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    thr = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        thr.update(thresholds)

    golden_doc = _read(golden_gap_path)
    stress_doc = _read(stress_gap_path)
    if golden_doc:
        golden_doc["_source_path"] = str(golden_gap_path.relative_to(ROOT)).replace("\\", "/")
    if stress_doc:
        stress_doc["_source_path"] = str(stress_gap_path.relative_to(ROOT)).replace("\\", "/")

    golden = _profile_from_gap(golden_doc, label="golden16")
    combined = _profile_from_gap(stress_doc, label="combined32")

    delta: dict[str, Any] = {}
    for key in ("router_hit_rate", "routing_oracle_gap", "cloud_skip_ratio", "deep_routing_recall"):
        gv = (golden.get("raw") or {}).get(key)
        cv = (combined.get("raw") or {}).get(key)
        if gv is not None and cv is not None:
            delta[f"{key}_combined32_minus_golden16"] = round(float(cv) - float(gv), 4)

    golden_ok, golden_checks = _passes_thresholds(golden.get("raw") or {}, thr)
    combined_ok, combined_checks = _passes_thresholds(combined.get("raw") or {}, thr)
    deep_bench_ok = golden_ok and combined_ok and bool(golden_doc) and bool(stress_doc)

    return {
        "schema": "ollama_shallow_cost_deep_bench_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "deep_bench_ok": deep_bench_ok,
        "gate_thresholds": thr,
        "profiles": {
            "golden16": golden,
            "combined32": combined,
        },
        "profile_gate_checks": {
            "golden16": {"ok": golden_ok, "checks": golden_checks},
            "combined32": {"ok": combined_ok, "checks": combined_checks},
        },
        "delta_combined32_minus_golden16": delta,
        "scope_note": "Shallow preprocess fixture only — not OS-wide API cost claim",
        "reproduce": "py scripts/build_ollama_shallow_cost_deep_bench_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-gap", type=Path, default=GOLDEN_GAP)
    ap.add_argument("--stress-gap", type=Path, default=STRESS_GAP)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_deep_bench(golden_gap_path=args.golden_gap, stress_gap_path=args.stress_gap)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["deep_bench_ok"],
                "out": str(args.out),
                "golden16_csr": (doc["profiles"]["golden16"]["raw"] or {}).get("cloud_skip_ratio"),
                "combined32_csr": (doc["profiles"]["combined32"]["raw"] or {}).get("cloud_skip_ratio"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["deep_bench_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
