#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TAXONOMY = ROOT / "docs" / "final" / "artifacts" / "general_compression_90pct_failure_taxonomy_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_compression_domain_guard_gate_v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Domain guard gate for general compression rollout.")
    ap.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tax = _load(args.taxonomy)
    failures = tax.get("failure_taxonomy") or []
    zero_tolerance_hits = [
        f for f in failures if isinstance(f, dict) and str(f.get("risk_mode", "")) == "zero_tolerance"
    ]
    domain_hits = [
        f for f in failures if isinstance(f, dict) and str(f.get("domain", "")) == "policy_legal_lite"
    ]
    auto_no_go = bool(zero_tolerance_hits or domain_hits)

    out = {
        "schema": "general_compression_domain_guard_gate_v1",
        "inputs": {"taxonomy": str(args.taxonomy.resolve())},
        "rules": {
            "zero_tolerance_domain_auto_no_go": True,
            "sensitive_domain_policy_legal_lite_auto_no_go": True,
        },
        "checks": {
            "zero_tolerance_failure_count": len(zero_tolerance_hits),
            "policy_legal_lite_failure_count": len(domain_hits),
        },
        "decision": "NO_GO" if auto_no_go else "GO",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "decision": out["decision"], "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
