#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def build_placeholder(name: str) -> dict[str, Any]:
    return {
        "model_name": name,
        "is_placeholder": True,
        "metrics": {
            "oos_f1": None,
            "oos_auc": None,
            "ece": None,
            "runtime_sec": None,
            "cost_usd": None,
        },
        "notes": "Fill with real baseline outputs from external SOTA run.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build SOTA benchmark adapter packet and comparison skeleton.")
    ap.add_argument("--full-canon-report-json", default="docs/final/artifacts/global_atom_full_canon_batch_report_latest.json")
    ap.add_argument("--onepager-json", default="docs/final/artifacts/global_atom_network_academic_onepager_latest.json")
    ap.add_argument("--baseline-a-json", default="")
    ap.add_argument("--baseline-b-json", default="")
    ap.add_argument("--baseline-c-json", default="")
    ap.add_argument("--output-json", default="docs/final/artifacts/global_atom_sota_benchmark_adapter_latest.json")
    args = ap.parse_args()

    rp = resolve(args.full_canon_report_json)
    opg = resolve(args.onepager_json)
    if not rp.is_file() or not opg.is_file():
        raise SystemExit("missing required input report/onepager")
    report = load(rp)
    one = load(opg)

    facts = one.get("key_facts") if isinstance(one.get("key_facts"), dict) else {}
    ours = {
        "model_name": "global_atom_network",
        "is_placeholder": False,
        "metrics": {
            # NOTE: these are framework-level metrics available now; not external SOTA F1/AUC yet.
            "node_count": facts.get("node_count"),
            "edge_count": facts.get("edge_count"),
            "counterfactual_mean_gap": facts.get("counterfactual_mean_gap"),
            "gate_status": facts.get("gate_status"),
            "batch_stages_ok": facts.get("batch_stages_ok"),
            "batch_stages_total": facts.get("batch_stages_total"),
        },
    }

    baseline_specs = [
        ("baseline_a", args.baseline_a_json, "sota_baseline_a"),
        ("baseline_b", args.baseline_b_json, "sota_baseline_b"),
        ("baseline_c", args.baseline_c_json, "sota_baseline_c"),
    ]
    baselines: dict[str, Any] = {}
    for key, path_str, default_name in baseline_specs:
        if path_str.strip():
            p = resolve(path_str)
            if p.is_file():
                doc = load(p)
                baselines[key] = {
                    "model_name": str(doc.get("model_name") or default_name),
                    "is_placeholder": bool(doc.get("is_placeholder", False)),
                    "metrics": doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {},
                    "notes": doc.get("notes"),
                    "source_json": str(p),
                }
                continue
        baselines[key] = build_placeholder(default_name)

    out = {
        "schema": "global_atom_sota_benchmark_adapter_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "ours": ours,
        "baselines": baselines,
        "comparison_policy": {
            "strict_note": "Do not claim SOTA outperformance until baseline metrics are non-placeholder and reproducible.",
            "required_baseline_metrics": ["oos_f1", "oos_auc", "ece", "runtime_sec", "cost_usd"],
        },
        "sources": {
            "full_canon_report_json": str(rp),
            "onepager_json": str(opg),
        },
    }

    outp = resolve(args.output_json)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(outp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

