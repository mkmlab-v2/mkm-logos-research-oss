# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.5, M:0.2}
# Balance: 92
# Purpose: Re-rank must-keep candidates and run tiny top-N sweep for Track A.
# Keywords: track_a, must_keep, priority, sweep, gate
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RULES_IN = ROOT / "docs" / "final" / "artifacts" / "track_a_failure_pattern_rules_v1.json"
RULES_PRIORITY = ROOT / "docs" / "final" / "artifacts" / "track_a_failure_pattern_rules_priority_v1.json"
AB_OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_must_keep_ab_result_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_must_keep_priority_sweep_v1.json"

PRIORITY_WORDS = {
    "not",
    "no",
    "never",
    "cannot",
    "policy",
    "track",
    "state",
    "phase",
    "risk",
    "gate",
    "timing",
    "bootstrap",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _priority_score(token: str) -> int:
    score = 0
    t = token.lower()
    if t in PRIORITY_WORDS:
        score += 50
    if any(ch.isdigit() for ch in t):
        score += 40
    if len(t) <= 4:
        score += 5
    return score


def _run_ab(top_n: int, rules_path: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_track_a_must_keep_ab_v1.py"),
        "--top-n",
        str(top_n),
        "--rules",
        str(rules_path),
    ]
    subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
    ab_doc = json.loads(AB_OUT.read_text(encoding="utf-8"))
    m = ab_doc.get("metrics", {})
    d = m.get("delta", {})
    gate = ab_doc.get("gate", {})
    treatment = m.get("treatment", {})
    return {
        "top_n": top_n,
        "decision": ab_doc.get("decision"),
        "saving": float(treatment.get("global_token_saving_rate", 0.0)),
        "jaccard": float(treatment.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "integrity": float(treatment.get("avg_sensitive_integrity", 0.0)),
        "delta_saving": float(d.get("global_token_saving_rate", 0.0)),
        "delta_jaccard": float(d.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "saving_floor_ok": bool(gate.get("saving_floor_ok", False)),
        "integrity_floor_ok": bool(gate.get("integrity_floor_ok", False)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rules-in", type=Path, default=RULES_IN)
    ap.add_argument("--rules-priority-out", type=Path, default=RULES_PRIORITY)
    ap.add_argument("--topn-list", type=str, default="1,2,3,4")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    rules_in = args.rules_in if args.rules_in.is_absolute() else ROOT / args.rules_in
    rules_priority_out = args.rules_priority_out if args.rules_priority_out.is_absolute() else ROOT / args.rules_priority_out
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rules_doc = json.loads(rules_in.read_text(encoding="utf-8"))
    candidates = [row for row in rules_doc.get("must_keep_candidates", []) if str(row.get("token") or "").strip()]
    ranked = sorted(
        candidates,
        key=lambda row: (_priority_score(str(row.get("token"))), row.get("missing_count", row.get("risk_count", 0))),
        reverse=True,
    )

    priority_doc = dict(rules_doc)
    priority_doc["schema"] = "track_a_failure_pattern_rules_priority_v1"
    priority_doc["generated_at_utc"] = _now_utc()
    priority_doc["priority_words"] = sorted(PRIORITY_WORDS)
    priority_doc["must_keep_candidates"] = ranked
    rules_priority_out.write_text(json.dumps(priority_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    topn_values = [int(x.strip()) for x in args.topn_list.split(",") if x.strip()]
    runs = [_run_ab(n, rules_priority_out) for n in topn_values]
    viable = [r for r in runs if r["saving_floor_ok"] and r["integrity_floor_ok"]]
    best = sorted(viable, key=lambda r: (r["delta_jaccard"], r["saving"]), reverse=True)[0] if viable else None

    out_doc = {
        "schema": "track_a_must_keep_priority_sweep_v1",
        "generated_at_utc": _now_utc(),
        "rules_priority": str(rules_priority_out),
        "topn_list": topn_values,
        "runs": runs,
        "viable_count": len(viable),
        "recommended": best,
        "decision": "GO_RECOMMENDED_TOPN" if best else "HOLD_BASELINE_TRACK_A",
    }
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": out_doc["decision"], "recommended": best}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
