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


def main() -> int:
    ap = argparse.ArgumentParser(description="Build final GO/NO_GO decision for global atom submission.")
    ap.add_argument("--bundle-json", default="docs/final/artifacts/global_atom_submission_bundle_latest.json")
    ap.add_argument("--gate-summary-json", default="docs/final/artifacts/multi_symbol_gate_summary_latest.json")
    ap.add_argument("--falsification-json", default="docs/final/artifacts/two_track_falsification_suite_latest.json")
    ap.add_argument("--freeze-json", default="docs/final/artifacts/global_atom_submission_freeze_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/global_atom_submission_go_nogo_latest.json")
    args = ap.parse_args()

    bp = resolve(args.bundle_json)
    gp = resolve(args.gate_summary_json)
    fp = resolve(args.falsification_json)
    zp = resolve(args.freeze_json)
    op = resolve(args.output_json)
    for p in (bp, gp, fp, zp):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    b = load(bp)
    g = load(gp)
    f = load(fp)
    z = load(zp)

    bundle_ready = bool(b.get("ready", False))
    gate_status = str(((g.get("summary") or {}).get("status")) or "HOLD")
    gate_ok = gate_status == "GO"
    falsification_ok = str(f.get("suite_status", "")) == "pass"
    freeze_ok = int(z.get("missing_count", 1)) == 0 and int(z.get("copied_count", 0)) > 0

    go = bundle_ready and gate_ok and falsification_ok and freeze_ok
    reasons: list[str] = []
    if not bundle_ready:
        reasons.append("bundle_not_ready")
    if not gate_ok:
        reasons.append("multi_symbol_gate_not_go")
    if not falsification_ok:
        reasons.append("falsification_not_pass")
    if not freeze_ok:
        reasons.append("freeze_incomplete")

    out = {
        "schema": "global_atom_submission_go_nogo_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "bundle_json": str(bp),
            "gate_summary_json": str(gp),
            "falsification_json": str(fp),
            "freeze_json": str(zp),
        },
        "decision": {
            "go": go,
            "status": "GO" if go else "NO_GO",
            "reasons": reasons,
        },
        "snapshot": {
            "bundle_ready": bundle_ready,
            "gate_status": gate_status,
            "falsification_suite_status": f.get("suite_status"),
            "freeze_copied_count": z.get("copied_count"),
            "freeze_missing_count": z.get("missing_count"),
        },
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

