#!/usr/bin/env python3
"""[HYPO] Fine min_conf sweep around 0.18 for holdout7 neutral_abstain (04-02) cohort."""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_MISS = ROOT / "reports/btrack_holdout7_headline_miss_report_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_holdout7_0402_conf_boundary_sweep_v1_latest.json"
WORK = ROOT / "reports/btrack_holdout7_0402_conf_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"

VARIANTS: list[dict[str, Any]] = [
    {"slug": "prod_min_conf_018", "min_direction_confidence": 0.18},
    {"slug": "min_conf_01795", "min_direction_confidence": 0.1795},
    {"slug": "min_conf_0179", "min_direction_confidence": 0.179},
    {"slug": "min_conf_01785", "min_direction_confidence": 0.1785},
    {"slug": "min_conf_0175", "min_direction_confidence": 0.175},
    {"slug": "min_conf_017", "min_direction_confidence": 0.17},
    {"slug": "margin020_min0179", "tie_break_min_margin": 0.02, "min_direction_confidence": 0.179},
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _apply(base: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(base)
    rules = dict(cfg.get("rules") or {})
    for key in ("tie_break_min_margin", "min_direction_confidence", "neutral_penalty"):
        if key in spec:
            rules[key] = spec[key]
    cfg["rules"] = rules
    return cfg


def _run_variant(slug: str, cfg: dict[str, Any], *, recent_trading_days: int) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    cfg_p = WORK / f"ens_{slug}.json"
    per = WORK / f"per_{slug}.json"
    score = WORK / f"score_{slug}.json"
    ev_out = WORK / f"eval_{slug}.json"
    cfg_p.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    for cmd in [
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            str(recent_trading_days),
            "--ensemble-config",
            str(cfg_p.relative_to(ROOT)),
            "--output",
            str(per.relative_to(ROOT)),
        ],
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(recent_trading_days),
            "--force-dual-leg-panel",
            "--btc-csv",
            str(BTC_CSV.relative_to(ROOT)),
            "--kospi-csv",
            str(KOSPI_CSV.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per.relative_to(ROOT)),
            "--output",
            str(score.relative_to(ROOT)),
        ],
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score.relative_to(ROOT)),
            "--output",
            str(ev_out.relative_to(ROOT)),
        ],
    ]:
        p = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stderr or p.stdout)
    return {"per_date": per, "eval": _load(ev_out)}


def _cohort_rows(per_path: Path, cohort_dates: list[str]) -> list[dict[str, Any]]:
    doc = _load(per_path)
    preds = {
        str(r.get("eval_date"))[:10]: str(r.get("predicted_direction") or "").lower()
        for r in (doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    }
    out: list[dict[str, Any]] = []
    for ed in cohort_dates:
        m = next((x for x in (_load(DEFAULT_MISS).get("misses") or []) if str(x.get("eval_date"))[:10] == ed), {})
        actual = str(m.get("actual_direction") or "").lower()
        pred = preds.get(ed, "neutral")
        out.append(
            {
                "eval_date": ed,
                "actual_direction": actual,
                "predicted_direction": pred,
                "hit": pred in ("bull", "bear") and pred == actual,
                "wrong_if_directional": pred in ("bull", "bear") and pred != actual,
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--miss-report", type=Path, default=DEFAULT_MISS)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.miss_report.is_file():
        print(f"Missing {args.miss_report}", file=sys.stderr)
        return 2

    miss_doc = _load(args.miss_report)
    cohort = [
        str(m.get("eval_date"))[:10]
        for m in (miss_doc.get("misses") or [])
        if isinstance(m, dict) and m.get("miss_kind") == "neutral_abstain_miss"
    ]
    base = _load(DEFAULT_CFG)
    rows: list[dict[str, Any]] = []
    for spec in VARIANTS:
        slug = str(spec["slug"])
        print(f"==> conf_boundary {slug}", file=sys.stderr)
        try:
            raw = _run_variant(slug, _apply(base, spec), recent_trading_days=args.recent_trading_days)
            ev = raw["eval"]
            m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
            cohort_rows = _cohort_rows(raw["per_date"], cohort)
            recovered = sum(1 for c in cohort_rows if c.get("hit"))
            rows.append(
                {
                    "slug": slug,
                    "rules": _apply(base, spec).get("rules"),
                    "pooled_directional_hit_rate": m.get("price_directional_hit_rate"),
                    "n_evaluated": m.get("n_evaluated"),
                    "cohort_per_day": cohort_rows,
                    "n_cohort_recovered_hits": recovered,
                    "n_cohort": len(cohort),
                }
            )
        except RuntimeError as exc:
            rows.append({"slug": slug, "error": str(exc)[:400]})

    ok = [r for r in rows if "pooled_directional_hit_rate" in r]
    report = {
        "schema": "btrack_holdout7_0402_conf_boundary_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "cohort_dates": cohort,
        "prod_min_conf_frozen": 0.18,
        "variants": rows,
        "verdict_ko": (
            "04-02는 conf<0.18에서 neutral→bull(실제 bear)로 틀린 방향 호출; "
            "prod min_conf=0.18 유지 권고. advisory 플래그만 ops shadow."
        ),
        "operator_lines": [
            f"- [MKM-0402-CONF] cohort n={len(cohort)} dates={cohort}",
        ],
    }
    for r in ok:
        c0402 = next((c for c in (r.get("cohort_per_day") or []) if c.get("eval_date") == "2026-04-02"), {})
        report["operator_lines"].append(
            f"- [MKM-0402-CONF] {r.get('slug')}: pooled={r.get('pooled_directional_hit_rate')} "
            f"04-02 pred={c0402.get('predicted_direction')} hit={c0402.get('hit')}"
        )

    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
