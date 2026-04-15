# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.5, M:0.2}
# Balance: 92
# Purpose: Sweep Track A must-keep top-N candidates for saving-floor recovery.
# Keywords: track_a, must_keep, sweep, topn, ab
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
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_must_keep_topn_sweep_v1.json"
AB_OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_must_keep_ab_result_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run_ab(top_n: int) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / "scripts" / "run_track_a_must_keep_ab_v1.py"), "--top-n", str(top_n)]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
    line = (proc.stdout or "").strip().splitlines()[-1]
    _ = json.loads(line)
    ab_doc = json.loads(AB_OUT.read_text(encoding="utf-8"))
    metrics = ab_doc.get("metrics", {})
    delta = metrics.get("delta", {})
    gate = ab_doc.get("gate", {})
    return {
        "top_n": top_n,
        "decision": ab_doc.get("decision"),
        "saving": float((metrics.get("treatment") or {}).get("global_token_saving_rate", 0.0)),
        "jaccard": float((metrics.get("treatment") or {}).get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "integrity": float((metrics.get("treatment") or {}).get("avg_sensitive_integrity", 0.0)),
        "delta_saving": float(delta.get("global_token_saving_rate", 0.0)),
        "delta_jaccard": float(delta.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "saving_floor_ok": bool(gate.get("saving_floor_ok", False)),
        "integrity_floor_ok": bool(gate.get("integrity_floor_ok", False)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topn-list", type=str, default="5,6,7,8")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    topn_values = [int(x.strip()) for x in args.topn_list.split(",") if x.strip()]
    runs = [_run_ab(n) for n in topn_values]

    viable = [r for r in runs if r["saving_floor_ok"] and r["integrity_floor_ok"]]
    best = sorted(viable, key=lambda r: (r["delta_jaccard"], r["saving"]), reverse=True)[0] if viable else None

    out_doc = {
        "schema": "track_a_must_keep_topn_sweep_v1",
        "generated_at_utc": _now_utc(),
        "topn_list": topn_values,
        "runs": runs,
        "viable_count": len(viable),
        "recommended": best,
        "decision": "GO_RECOMMENDED_TOPN" if best else "HOLD_BASELINE_TRACK_A",
    }
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out": str(out_path), "decision": out_doc["decision"], "recommended": best}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
