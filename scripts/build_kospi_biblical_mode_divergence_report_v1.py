# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.84, L:0.86, K:0.58, M:0.7}
# Balance: 84
# Purpose: Compare KOSPI biblical gate modes (equivalent_n vs recent) and emit divergence alert report.
# Keywords: kospi, biblical, gate, divergence, alert
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ART = Path("docs/final/artifacts")
CANONICAL_DEFAULT = ART / "kospi_biblical_single_lane_commercial_gate_autonomous_latest.json"
RECENT_DEFAULT = ART / "_tmp_kospi_biblical_single_lane_commercial_gate_recent_min30.json"
OUT_DEFAULT = ART / "kospi_biblical_mode_divergence_report_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _f(x: Any, d: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return d


def build(
    canonical: dict[str, Any],
    recent: dict[str, Any],
    accuracy_gap_th: float,
    dom_gap_th: float,
) -> dict[str, Any]:
    c_ext = ((canonical.get("gates") or {}).get("external_reality_gate") or {}).get("active_metrics") or {}
    r_ext = ((recent.get("gates") or {}).get("external_reality_gate") or {}).get("active_metrics") or {}

    c_mode = str(((canonical.get("gates") or {}).get("external_reality_gate") or {}).get("mode", "unknown"))
    r_mode = str(((recent.get("gates") or {}).get("external_reality_gate") or {}).get("mode", "unknown"))

    c_acc = _f(c_ext.get("accuracy"))
    r_acc = _f(r_ext.get("accuracy"))
    c_dom = _f(c_ext.get("dominant_share"), 1.0)
    r_dom = _f(r_ext.get("dominant_share"), 1.0)

    acc_gap = round(abs(c_acc - r_acc), 6)
    dom_gap = round(abs(c_dom - r_dom), 6)

    c_blockers = [str(x) for x in (canonical.get("blockers") or [])]
    r_blockers = [str(x) for x in (recent.get("blockers") or [])]

    blocker_changed = sorted(c_blockers) != sorted(r_blockers)
    mode_changed = c_mode != r_mode

    reasons: list[str] = []
    if mode_changed:
        reasons.append(f"external_mode_changed:{c_mode}->{r_mode}")
    if acc_gap >= accuracy_gap_th:
        reasons.append(f"accuracy_gap={acc_gap}")
    if dom_gap >= dom_gap_th:
        reasons.append(f"dominant_share_gap={dom_gap}")
    if blocker_changed:
        reasons.append("blocker_set_changed")

    alert = len(reasons) > 0

    return {
        "schema": "kospi_biblical_mode_divergence_report_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "canonical_path": str(CANONICAL_DEFAULT.as_posix()),
            "recent_path": str(RECENT_DEFAULT.as_posix()),
        },
        "thresholds": {
            "accuracy_gap_alert": accuracy_gap_th,
            "dominant_share_gap_alert": dom_gap_th,
        },
        "canonical": {
            "stage": canonical.get("stage"),
            "mode": c_mode,
            "blockers": c_blockers,
            "external_metrics": {
                "accuracy": c_acc,
                "n_samples": int(_f(c_ext.get("n_samples"), 0.0)),
                "dominant_share": c_dom,
                "mixed_bull_capture": _f(c_ext.get("mixed_bull_capture")),
            },
        },
        "recent": {
            "stage": recent.get("stage"),
            "mode": r_mode,
            "blockers": r_blockers,
            "external_metrics": {
                "accuracy": r_acc,
                "n_samples": int(_f(r_ext.get("n_samples"), 0.0)),
                "dominant_share": r_dom,
                "mixed_bull_capture": _f(r_ext.get("mixed_bull_capture")),
            },
        },
        "diff": {
            "mode_changed": mode_changed,
            "blocker_set_changed": blocker_changed,
            "accuracy_gap_abs": acc_gap,
            "dominant_share_gap_abs": dom_gap,
        },
        "alert": alert,
        "alert_reasons": reasons,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build KOSPI biblical mode divergence report")
    ap.add_argument("--canonical", type=Path, default=CANONICAL_DEFAULT)
    ap.add_argument("--recent", type=Path, default=RECENT_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--accuracy-gap-alert", type=float, default=0.08)
    ap.add_argument("--dominant-share-gap-alert", type=float, default=0.08)
    args = ap.parse_args()

    canonical = _load(args.canonical)
    recent = _load(args.recent)
    report = build(canonical, recent, args.accuracy_gap_alert, args.dominant_share_gap_alert)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve()), "alert": report["alert"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
