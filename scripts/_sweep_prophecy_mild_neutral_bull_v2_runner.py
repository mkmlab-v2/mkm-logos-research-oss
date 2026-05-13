"""One-off batch: mild downside_force_bear + neutral_bps / bull_reversal sweep (B-track, local)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_btrack_prophecy_score_from_ohlcv.py"
EVAL = ROOT / "scripts" / "eval_prophecy_hit_rate_v1.py"
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ROOT / "reports" / "prophecy_mild_plus_neutral_bull_sweep_v2_latest.json"

BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"

MILD = [
    "--btc-csv",
    str(BTC_CSV),
    "--downside-force-bear-enable",
    "--downside-force-bear-lookback",
    "5",
    "--downside-force-bear-min-down-days",
    "3",
    "--downside-force-bear-min-cum-down-pct",
    "4.5",
    "--recent-trading-days",
    "180",
]


def streaks_ge3(rows: list[dict]) -> int:
    usable = [r for r in rows if isinstance(r, dict) and r.get("eval_date")]
    usable.sort(key=lambda r: str(r.get("eval_date") or ""))
    runs = 0
    cur = 0
    for r in usable:
        pd = str(r.get("predicted_direction") or "").strip().lower()
        ad = str(r.get("actual_direction") or "").strip().lower()
        if not pd or not ad:
            continue
        if pd not in ("bull", "bear", "neutral") or ad not in ("bull", "bear", "neutral"):
            continue
        if pd != ad:
            cur += 1
        else:
            if cur >= 3:
                runs += 1
            cur = 0
    if cur >= 3:
        runs += 1
    return runs


def main() -> int:
    profiles: list[tuple[str, list[str]]] = [
        ("mild_ref", []),
        ("mild_nbps_3", ["--neutral-bps", "3"]),
        ("mild_nbps_12", ["--neutral-bps", "12"]),
        ("mild_nbps_25", ["--neutral-bps", "25"]),
        ("mild_br_lb3_th5", ["--bull-reversal-lookback", "3", "--bull-reversal-threshold-pct", "5"]),
        ("mild_br_lb5_th8", ["--bull-reversal-lookback", "5", "--bull-reversal-threshold-pct", "8"]),
        (
            "mild_br_lb3_shock",
            [
                "--bull-reversal-lookback",
                "3",
                "--bull-reversal-threshold-pct",
                "5.5",
                "--bull-reversal-enable-shock-cutoff",
            ],
        ),
        (
            "mild_nbps10_br_ts_dg",
            [
                "--neutral-bps",
                "10",
                "--bull-reversal-lookback",
                "4",
                "--bull-reversal-threshold-pct",
                "6",
                "--bull-reversal-two-stage-enable",
                "--bull-reversal-down-guard-enable",
            ],
        ),
    ]

    rows_out: list[dict] = []
    for pid, extra in profiles:
        score_path = ART / f"btrack_prophecy_score_{pid}_v2_latest.json"
        eval_path = ART / f"prophecy_hit_rate_eval_{pid}_v2_latest.json"
        cmd_b = [sys.executable, str(BUILD), *MILD, *extra, "--output", str(score_path)]
        rb = subprocess.run(cmd_b, cwd=str(ROOT))
        if rb.returncode != 0:
            rows_out.append({"profile_id": pid, "error": "build_failed", "build_exit": rb.returncode})
            continue
        cmd_e = [
            sys.executable,
            str(EVAL),
            "--run-mode",
            "price",
            "--score-json",
            str(score_path),
            "--output",
            str(eval_path),
        ]
        re = subprocess.run(cmd_e, cwd=str(ROOT))
        if re.returncode != 0:
            rows_out.append({"profile_id": pid, "error": "eval_failed", "eval_exit": re.returncode})
            continue
        doc = json.loads(score_path.read_text(encoding="utf-8"))
        srows = doc.get("rows") or []
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
        m = ev.get("metrics") or {}
        hit = m.get("price_directional_hit_rate")
        n = m.get("n_evaluated") or 0
        ph = m.get("price_hits")
        n_fail = (n - ph) if isinstance(n, int) and isinstance(ph, int) else None
        fr = (n_fail / n) if (isinstance(n, int) and n > 0 and n_fail is not None) else None
        rows_out.append(
            {
                "profile_id": pid,
                "extra_args": extra,
                "hit_rate": hit,
                "n_evaluated": n,
                "price_hits": ph,
                "n_fail": n_fail,
                "failure_rate": fr,
                "streaks_ge3": streaks_ge3(srows),
                "score_path": str(score_path.relative_to(ROOT)).replace("\\", "/"),
                "eval_path": str(eval_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    def rank_key(r: dict) -> tuple[float, int]:
        if r.get("hit_rate") is None:
            return (-1.0, 999)
        streak = r.get("streaks_ge3")
        if streak is None:
            streak = 999
        return (float(r["hit_rate"]), -int(streak))

    ok = [r for r in rows_out if r.get("hit_rate") is not None]
    best_hr = max(ok, key=rank_key) if ok else None
    best_combo = None
    if ok:

        def combo_key(r: dict) -> tuple[float, float, int]:
            return (
                float(r["hit_rate"]),
                -float(r.get("failure_rate") or 1.0),
                -int(r.get("streaks_ge3") or 999),
            )

        best_combo = max(ok, key=combo_key)

    report = {
        "schema": "prophecy_mild_plus_neutral_bull_sweep_v2",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base": "downside_force_bear_mild + recent_trading_days=180",
        "rows": rows_out,
        "best_by_hit_then_streaks": best_hr,
        "best_by_hit_failure_streak": best_combo,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
