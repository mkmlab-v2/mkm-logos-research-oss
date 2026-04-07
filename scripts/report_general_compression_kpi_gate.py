#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "general_compression_ab_result_summary_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_compression_kpi_gate_v2.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute GO/NO_GO from general compression AB summary.")
    ap.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _load(args.summary)
    runs = doc.get("runs") or []
    by_label = {str(r.get("label")): r for r in runs if isinstance(r, dict)}
    base = by_label.get("baseline", {})
    trt = by_label.get("treatment", {})

    saving_ok = float(trt.get("global_token_saving_rate", 0.0)) > float(base.get("global_token_saving_rate", 0.0))
    fidelity_ok = float(trt.get("avg_reconstruction_fidelity_jaccard", 0.0)) >= 0.60
    integrity_ok = float(trt.get("avg_sensitive_integrity", 0.0)) >= 0.99
    go = saving_ok and fidelity_ok and integrity_ok

    out = {
        "schema": "general_compression_kpi_gate_v2",
        "inputs": {"summary": str(args.summary.resolve())},
        "checks": {
            "saving_improved_vs_baseline": saving_ok,
            "fidelity_floor_ok": fidelity_ok,
            "sensitive_integrity_ok": integrity_ok,
        },
        "decision": "GO" if go else "NO_GO",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "decision": out["decision"], "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
