#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    apath = ROOT / "docs" / "final" / "artifacts" / "global_atom_sota_benchmark_adapter_latest.json"
    outp = ROOT / "docs" / "final" / "artifacts" / "global_atom_sota_baseline_readiness_latest.json"
    if not apath.is_file():
        raise SystemExit(f"missing adapter: {apath}")
    ad = json.loads(apath.read_text(encoding="utf-8"))
    baselines = ad.get("baselines") if isinstance(ad.get("baselines"), dict) else {}

    rows = []
    all_ready = True
    for key, b in baselines.items():
        if not isinstance(b, dict):
            continue
        metrics = b.get("metrics") if isinstance(b.get("metrics"), dict) else {}
        req = ["oos_f1", "oos_auc", "ece", "runtime_sec", "cost_usd"]
        missing = [m for m in req if metrics.get(m) is None]
        ready = (not bool(b.get("is_placeholder", False))) and (len(missing) == 0)
        if not ready:
            all_ready = False
        rows.append(
            {
                "baseline_key": key,
                "model_name": b.get("model_name"),
                "ready": ready,
                "missing_metrics": missing,
                "is_placeholder": bool(b.get("is_placeholder", False)),
            }
        )

    out = {
        "schema": "global_atom_sota_baseline_readiness_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "all_ready": all_ready,
        "rows": rows,
    }
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(outp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

