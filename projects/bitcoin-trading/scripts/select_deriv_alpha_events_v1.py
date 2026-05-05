#!/usr/bin/env python3
"""
select_deriv_alpha_events_v1 — EV 리포트에서 후보 이벤트 1~2개 자동 선별.

Fact-Lock:
  - 실매매 트리거 금지. 연구용 후보 추천만 출력.
  - 표본 부족 시 no_candidate로 명시.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _workspace_root() -> Path:
    here = Path(__file__).resolve()
    try:
        if (
            here.parent.name == "scripts"
            and here.parent.parent.name == "bitcoin-trading"
            and here.parents[2].name == "projects"
        ):
            root = here.parents[3]
            if (root / "AGENTS.md").is_file():
                return root
    except IndexError:
        pass
    for parent in here.parents:
        if (
            (parent / "AGENTS.md").is_file()
            and (parent / "projects" / "bitcoin-trading").is_dir()
        ):
            return parent
    return here.parents[3] if len(here.parents) > 3 else here.parent


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _i(x: Any) -> Optional[int]:
    if x is None:
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def score_event_horizon(
    event_name: str,
    horizon: str,
    horizon_payload: Dict[str, Any],
    min_count: int,
) -> Optional[Dict[str, Any]]:
    net = horizon_payload.get("net_after_cost") or {}
    raw = horizon_payload.get("raw") or {}
    cnt = _i(net.get("count"))
    if cnt is None or cnt < min_count:
        return None
    mean = _f(net.get("mean"))
    win = _f(net.get("win_rate"))
    mean_bps_net = _f(horizon_payload.get("mean_bps_net"))
    if mean is None or win is None or mean_bps_net is None:
        return None
    if mean <= 0:
        return None
    # 단순 점수: 기대값 우선 + 승률 보조
    score = (mean_bps_net * 0.7) + ((win - 0.5) * 100.0 * 0.3)
    return {
        "event": event_name,
        "horizon_sec": int(horizon),
        "count": cnt,
        "mean_net": mean,
        "mean_bps_net": mean_bps_net,
        "win_rate_net": win,
        "mean_bps_raw": _f(horizon_payload.get("mean_bps_raw")),
        "score": score,
        "raw_count": _i(raw.get("count")),
    }


def build_alpha_profile(sel: Dict[str, Any]) -> Dict[str, Any]:
    # 연구용 매핑: 점수 기반 비중 제안 (집행 권한 없음)
    score = float(sel["score"])
    # 보수적으로 0.2~0.8 클램프
    size = max(0.2, min(0.8, 0.2 + score / 100.0))
    conf = "low"
    if sel["count"] >= 50 and sel["win_rate_net"] >= 0.55:
        conf = "high"
    elif sel["count"] >= 20:
        conf = "medium"
    return {
        "alpha_score": round(score, 6),
        "size_multiplier": round(size, 4),
        "confidence_band": conf,
        "execution_authority": "none_research_only",
    }


def main() -> int:
    ws = _workspace_root()
    parser = argparse.ArgumentParser(description="Select top deriv alpha event candidates from EV report.")
    parser.add_argument(
        "--ev-report",
        type=Path,
        default=ws / "reports" / "deriv_factor_ev_report_v1.json",
        help="Input EV report JSON path",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ws / "reports" / "deriv_alpha_event_candidates_v1.json",
        help="Output candidates JSON path",
    )
    parser.add_argument("--top-k", type=int, default=2, help="Number of candidates to keep")
    parser.add_argument("--min-count", type=int, default=20, help="Minimum sample count per event/horizon")
    args = parser.parse_args()

    if not args.ev_report.is_file():
        raise SystemExit(f"EV report not found: {args.ev_report}")

    report = json.loads(args.ev_report.read_text(encoding="utf-8"))
    events = report.get("events") or {}
    scored: List[Dict[str, Any]] = []
    for event_name, payload in events.items():
        horizon_eval = payload.get("horizon_eval") or {}
        for horizon, hv in horizon_eval.items():
            s = score_event_horizon(event_name, horizon, hv, args.min_count)
            if s:
                s["alpha_profile"] = build_alpha_profile(s)
                scored.append(s)

    scored.sort(key=lambda x: x["score"], reverse=True)
    top_k = max(1, int(args.top_k))
    selected = scored[:top_k]

    out: Dict[str, Any] = {
        "schema": "deriv_alpha_event_candidates_v1",
        "source_ev_report": str(args.ev_report),
        "symbol": report.get("symbol"),
        "row_count": report.get("row_count"),
        "selection_config": {
            "top_k": top_k,
            "min_count": int(args.min_count),
        },
        "candidate_count": len(selected),
        "status": "ok" if selected else "no_candidate",
        "candidates": selected,
        "note": "research-only; final execution must pass existing governance gates.",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "status": out["status"],
                "candidate_count": out["candidate_count"],
                "out_json": str(args.out_json),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
