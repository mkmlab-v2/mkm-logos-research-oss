# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.72, L:0.84, K:0.58, M:0.52}
# Balance: 84
# Purpose: Emit dense calendar-day stub JSONLs so dated_source_snapshots_asof_eval_date tracks eval_date (B-track tier B).
# Keywords: btrack, sasang, myeongni, jsonl, sidecar
"""Write calendar-dense stub JSONLs for sasang dynamics + myeongni 16-state experiment paths.

Default range covers 2026 Q1 score rows through mid-April. Re-run to extend end_date.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SASANG_OUT = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
DEFAULT_MYEONGNI_OUT = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"


def _daterange(d0: date, d1: date) -> list[date]:
    out: list[date] = []
    cur = d0
    while cur <= d1:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2026-01-01", help="First calendar day (YYYY-MM-DD).")
    ap.add_argument("--end", default="2026-04-30", help="Last calendar day (YYYY-MM-DD).")
    ap.add_argument("--sasang-out", type=Path, default=DEFAULT_SASANG_OUT)
    ap.add_argument("--myeongni-out", type=Path, default=DEFAULT_MYEONGNI_OUT)
    args = ap.parse_args()

    d0 = date.fromisoformat(args.start)
    d1 = date.fromisoformat(args.end)
    days = _daterange(d0, d1)
    mt_cycle = ("bull", "bear", "sideways")
    hyp_cycle = ("accumulation", "distribution", "phase_transition")

    sas_lines: list[dict] = []
    my_lines: list[dict] = []
    for i, d in enumerate(days):
        ts_sas = f"{d.isoformat()}T12:00:00+00:00"
        ts_my = f"{d.isoformat()}T13:00:00Z"
        mt = mt_cycle[i % 3]
        h = 0.45 + (i % 10) * 0.015
        c = min(0.62, max(0.38, 1.0 - h))
        h = min(0.62, max(0.38, h))
        vr = min(0.65, 0.48 + (i % 7) * 0.02)
        sas_lines.append(
            {
                "ts_utc": ts_sas,
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "stub": True,
                "a_track_autobind_forbidden": True,
                "mapping_target": mt,
                "regime_hypothesis": hyp_cycle[i % 3],
                "machine_readables": {
                    "heat_proxy": round(h, 3),
                    "cold_proxy": round(c, 3),
                    "volatility_rarefaction_proxy": round(vr, 3),
                },
            }
        )
        sid = 6 + (i % 11)
        cr = min(0.82, 0.55 + (i % 8) * 0.03)
        scr = min(0.12, 0.05 + (i % 5) * 0.012)
        my_lines.append(
            {
                "ts_utc": ts_my,
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "stub": True,
                "state_id": sid,
                "mapping_target": mt,
                "consistency_rate": round(cr, 2),
                "self_contradiction_rate": round(scr, 3),
                "run_id": "calendar_stub_through_202604",
            }
        )

    args.sasang_out.parent.mkdir(parents=True, exist_ok=True)
    args.myeongni_out.parent.mkdir(parents=True, exist_ok=True)
    args.sasang_out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in sas_lines) + "\n", encoding="utf-8")
    args.myeongni_out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in my_lines) + "\n", encoding="utf-8")
    print(f"WROTE {len(sas_lines)} lines -> {args.sasang_out}")
    print(f"WROTE {len(my_lines)} lines -> {args.myeongni_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
