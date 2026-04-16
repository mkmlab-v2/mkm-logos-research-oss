# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-22 E2 spike with candidate pool expansion in evaluate_report.
# Keywords: track_a, week22, e2, candidate_pool, spike
#!/usr/bin/env python3
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

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_e2_candidate_pool_spike_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_V2)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--saving-floor", type=float, default=0.49)
    ap.add_argument("--jaccard-floor", type=float, default=0.85)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    ap.add_argument("--pool-size", type=int, default=5)
    args = ap.parse_args()

    doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    report = evaluate_report(
        doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy="A",
        intensity="extreme",
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=0.54,
        sensitive_max_saving_rate=0.5,
        hangul_max_saving_rate=0.48,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
        enable_candidate_pool_expansion=True,
        candidate_pool_max_variants=max(1, int(args.pool_size)),
    )
    metrics = report.get("compression_metrics", {})
    gate = {
        "saving_floor_ok": float(metrics.get("global_token_saving_rate", 0.0)) >= args.saving_floor,
        "jaccard_floor_ok": float(metrics.get("avg_reconstruction_fidelity_jaccard", 0.0)) >= args.jaccard_floor,
        "integrity_floor_ok": float(metrics.get("avg_sensitive_integrity", 0.0)) >= args.integrity_floor,
    }
    decision = "GO_W22_E2_CANDIDATE_POOL" if all(gate.values()) else "HOLD_W22_E2_NO_VIABLE"

    pool_selected_counts: dict[str, int] = {}
    for row in metrics.get("cases", []) or []:
        route = row.get("route") or {}
        if isinstance(route, dict):
            meta = route.get("candidate_pool")
            if isinstance(meta, dict):
                key = str(meta.get("candidate_pool_selected") or "unknown")
                pool_selected_counts[key] = pool_selected_counts.get(key, 0) + 1

    out_doc: dict[str, Any] = {
        "schema": "track_a_week22_e2_candidate_pool_spike_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "pool_size": int(args.pool_size),
            "floors": {
                "saving_floor": args.saving_floor,
                "jaccard_floor": args.jaccard_floor,
                "integrity_floor": args.integrity_floor,
            },
        },
        "metrics": {
            "global_token_saving_rate": float(metrics.get("global_token_saving_rate", 0.0)),
            "avg_reconstruction_fidelity_jaccard": float(metrics.get("avg_reconstruction_fidelity_jaccard", 0.0)),
            "avg_sensitive_integrity": float(metrics.get("avg_sensitive_integrity", 0.0)),
            "candidate_pool_selected_counts": pool_selected_counts,
        },
        "gate": gate,
        "decision": decision,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
