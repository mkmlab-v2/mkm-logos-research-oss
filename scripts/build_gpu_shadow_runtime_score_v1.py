#!/usr/bin/env python3
"""Build shadow-only runtime score artifact (no live auto-binding)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SIGNOFF = ART / "prophecy_release_signoff_packet_v1_latest.json"
DEFAULT_GRAPH = ART / "gpu_graph_anomaly_sweep_v1_latest.json"
DEFAULT_RESWEEP = ART / "gpu_universal_precursor_resweep_v1_latest.json"
DEFAULT_OUT = ART / "gpu_shadow_runtime_score_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--resweep-json", type=Path, default=DEFAULT_RESWEEP)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    signoff = _load(args.signoff_json)
    graph = _load(args.graph_json)
    resweep = _load(args.resweep_json)

    checks = signoff.get("checks") if isinstance(signoff.get("checks"), dict) else {}
    signoff_strength = sum(1 for v in checks.values() if v is True) / max(1, len(checks))

    am = graph.get("anomaly_metrics") if isinstance(graph.get("anomaly_metrics"), dict) else {}
    high_bridge = float(am.get("cross_bridge_density_high_band") or 0.0)
    mid_bridge = float(am.get("cross_bridge_density_mid_band") or 0.0)
    graph_stability = _clip01(1.0 - abs(high_bridge - mid_bridge))

    resweep_status = str(resweep.get("status") or "")
    precursor_score = 1.0 if resweep_status == "go_research_robust" else 0.4

    shadow_score = _clip01((0.45 * signoff_strength) + (0.30 * graph_stability) + (0.25 * precursor_score))
    shadow_decision = "SHADOW_GO" if shadow_score >= 0.75 else "SHADOW_WATCH"

    out = {
        "schema": "gpu_shadow_runtime_score_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "inputs": {
            "signoff_json": str(args.signoff_json).replace("\\", "/"),
            "graph_json": str(args.graph_json).replace("\\", "/"),
            "resweep_json": str(args.resweep_json).replace("\\", "/"),
        },
        "components": {
            "signoff_strength": round(signoff_strength, 6),
            "graph_stability": round(graph_stability, 6),
            "precursor_resweep_score": round(precursor_score, 6),
        },
        "shadow": {
            "runtime_score_0_1": round(shadow_score, 6),
            "runtime_decision": shadow_decision,
        },
        "constraints": {
            "shadow_only": True,
            "no_auto_live_binding": True,
        },
        "notes_ko": [
            "본 점수는 섀도우 모니터링/알림용이며 자동 매매 트리거로 연결하지 않는다."
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"runtime_score={out['shadow']['runtime_score_0_1']}")
    print(f"runtime_decision={out['shadow']['runtime_decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
