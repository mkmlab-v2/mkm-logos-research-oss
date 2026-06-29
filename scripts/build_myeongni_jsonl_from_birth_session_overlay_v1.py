#!/usr/bin/env python3
"""Per-day myeongni JSONL: birth-chain lens + session wall-clock + market overlay policy.

B-track research spike. Does not replace v1_latest / golden sidecar without OOS proof.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.market_myeongni_overlay_engine_v1 import (  # noqa: E402
    apply_market_myeongni_overlay,
    load_overlay_policy,
)

DEFAULT_POLICY = ROOT / "data/market_myeongni/market_myeongni_overlay_policy_v1.json"
DEFAULT_BIRTH_LENS = ROOT / "docs/final/artifacts/myeongni_independent_lens_from_chain_latest.json"
DEFAULT_SESSION_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_MYEONGNI_OUT = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.birth_session_overlay_30y_v1.jsonl"
DEFAULT_SASANG_OUT = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.birth_session_overlay_30y_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mapping_from_direction(score: float, band: float) -> str:
    if score > band:
        return "bull"
    if score < -band:
        return "bear"
    return "sideways"


def _load_session_by_day(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        ed = str(row.get("eval_date") or row.get("ts_utc") or "")[:10]
        if ed:
            out[ed] = row
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--birth-lens-json", type=Path, default=DEFAULT_BIRTH_LENS)
    ap.add_argument("--session-jsonl", type=Path, default=DEFAULT_SESSION_JSONL)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--overlay-band", type=float, default=0.08, help="bull/bear vs sideways threshold on overlay score")
    ap.add_argument("--session-weight", type=float, default=0.35, help="Blend session_direction into base")
    ap.add_argument("--myeongni-out", type=Path, default=DEFAULT_MYEONGNI_OUT)
    ap.add_argument("--sasang-out", type=Path, default=DEFAULT_SASANG_OUT)
    args = ap.parse_args()

    birth = json.loads(args.birth_lens_json.read_text(encoding="utf-8-sig"))
    policy = load_overlay_policy(args.policy_json)
    session_by_day = _load_session_by_day(args.session_jsonl)
    if not session_by_day:
        raise SystemExit(f"no session rows: {args.session_jsonl}")

    scores = birth.get("scores") if isinstance(birth.get("scores"), dict) else {}
    base_d = float(scores.get("direction_score") or 0.0)
    base_c = float(scores.get("confidence") or 0.5)
    stream = birth.get("myeongri_stream_outputs") if isinstance(birth.get("myeongri_stream_outputs"), dict) else {}
    birth_state_id = stream.get("state_id")
    try:
        birth_state_id = int(birth_state_id) if birth_state_id is not None else None
    except (TypeError, ValueError):
        birth_state_id = None

    my_lines: list[dict[str, Any]] = []
    sa_lines: list[dict[str, Any]] = []
    for ed in sorted(session_by_day):
        sess = session_by_day[ed]
        sess_score = float(sess.get("session_direction_score") or 0.0)
        blended_base = max(-1.0, min(1.0, (1.0 - args.session_weight) * base_d + args.session_weight * sess_score))
        sid = birth_state_id
        if sid is None:
            sid = 6 + (hash(ed) % 11)
        out_d, out_c, applied = apply_market_myeongni_overlay(
            base_direction=blended_base,
            base_confidence=base_c,
            state_id=sid,
            policy=policy,
        )
        mt = _mapping_from_direction(out_d, args.overlay_band)
        my_lines.append(
            {
                "ts_utc": f"{ed}T13:00:00Z",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "stub": False,
                "source": "birth_session_overlay_v1",
                "eval_date": ed,
                "mapping_target": mt,
                "overlay_direction_score": round(out_d, 6),
                "overlay_confidence": round(out_c, 6),
                "birth_direction_score": round(base_d, 6),
                "session_direction_score": round(sess_score, 6),
                "state_id": sid,
                "overlay_applied": applied,
                "run_id": "birth_session_overlay_30y_v1",
            }
        )
        sa_lines.append(
            {
                "ts_utc": f"{ed}T12:00:00+00:00",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "stub": False,
                "source": "birth_session_overlay_v1",
                "eval_date": ed,
                "mapping_target": mt,
                "regime_hypothesis": "phase_transition",
                "machine_readables": {"overlay_direction_score": round(out_d, 6)},
            }
        )

    args.myeongni_out.parent.mkdir(parents=True, exist_ok=True)
    args.sasang_out.parent.mkdir(parents=True, exist_ok=True)
    args.myeongni_out.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in my_lines) + "\n",
        encoding="utf-8",
    )
    args.sasang_out.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in sa_lines) + "\n",
        encoding="utf-8",
    )

    from collections import Counter

    c = Counter(x["mapping_target"] for x in my_lines)
    meta = {
        "schema": "myeongni_jsonl_from_birth_session_overlay_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "n_days": len(my_lines),
        "mapping_target_counts": dict(c),
        "birth_lens": str(args.birth_lens_json.relative_to(ROOT)).replace("\\", "/"),
        "session_jsonl": str(args.session_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "myeongni_out": str(args.myeongni_out.relative_to(ROOT)).replace("\\", "/"),
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
