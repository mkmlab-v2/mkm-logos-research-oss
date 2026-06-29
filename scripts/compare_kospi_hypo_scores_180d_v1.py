#!/usr/bin/env python3
"""[HYPO] Compare two KOSPI ensemble score JSONs on 180d panel (monthly bands + disagreements)."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _kospi_map(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(r["eval_date"]): r
        for r in (doc.get("rows") or [])
        if str(r.get("instrument", "")).lower() == "kospi"
    }


def _hit(r: dict[str, Any]) -> bool:
    return r.get("predicted_direction") == r.get("actual_direction")


def _gate_btc_lens_mean(gates_path: Path) -> float | None:
    if not gates_path.is_file():
        return None
    g = json.loads(gates_path.read_text(encoding="utf-8-sig"))
    gates = (g.get("tracks") or {}).get("per_date_lens", {}).get("gates") or []
    for gate in gates:
        if gate.get("gate_id") == "lens_wf_mean_test_accuracy":
            obs = gate.get("observed") or {}
            v = obs.get("mean_test_accuracy")
            return float(v) if isinstance(v, (int, float)) else None
    return None


def compare(
    *,
    label_a: str,
    score_a: Path,
    config_a: str,
    gates_a: Path | None,
    label_b: str,
    score_b: Path,
    config_b: str,
    gates_b: Path | None,
) -> dict[str, Any]:
    ma = _kospi_map(json.loads(score_a.read_text(encoding="utf-8-sig")))
    mb = _kospi_map(json.loads(score_b.read_text(encoding="utf-8-sig")))
    dates = sorted(set(ma) & set(mb))
    if not dates:
        raise SystemExit("no overlapping kospi eval dates")

    month_a: dict[str, dict[str, int]] = defaultdict(lambda: {"h": 0, "n": 0})
    month_b: dict[str, dict[str, int]] = defaultdict(lambda: {"h": 0, "n": 0})
    agree_same_pred = disagree = 0
    only_a_hit = only_b_hit = both_hit = both_miss = 0
    disagree_days: list[dict[str, Any]] = []

    for d in dates:
        ra, rb = ma[d], mb[d]
        ha, hb = _hit(ra), _hit(rb)
        m = d[:7]
        month_a[m]["n"] += 1
        month_b[m]["n"] += 1
        if ha:
            month_a[m]["h"] += 1
        if hb:
            month_b[m]["h"] += 1

        pa, pb = ra.get("predicted_direction"), rb.get("predicted_direction")
        if pa == pb:
            agree_same_pred += 1
            if ha:
                both_hit += 1
            else:
                both_miss += 1
        else:
            disagree += 1
            if ha and not hb:
                only_a_hit += 1
            elif hb and not ha:
                only_b_hit += 1
            disagree_days.append(
                {
                    "eval_date": d,
                    f"{label_a}_pred": pa,
                    f"{label_b}_pred": pb,
                    "actual": ra.get("actual_direction"),
                    f"{label_a}_hit": ha,
                    f"{label_b}_hit": hb,
                    "daily_return_pct": round(float(ra.get("daily_return", 0)) * 100, 4),
                }
            )

    n = len(dates)
    ha_tot = sum(1 for d in dates if _hit(ma[d]))
    hb_tot = sum(1 for d in dates if _hit(mb[d]))
    month_table = []
    for m in sorted(set(month_a) | set(month_b)):
        na, nb = month_a[m], month_b[m]
        month_table.append(
            {
                "month": m,
                f"{label_a}_hit_rate": round(na["h"] / na["n"], 4) if na["n"] else None,
                f"{label_b}_hit_rate": round(nb["h"] / nb["n"], 4) if nb["n"] else None,
                "n": na["n"],
                f"delta_{label_b}_minus_{label_a}": round((nb["h"] / nb["n"]) - (na["h"] / na["n"]), 4)
                if na["n"] and nb["n"]
                else None,
            }
        )

    return {
        "schema": "kospi_hypo_scores_180d_compare_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "panel_days": n,
        label_a: {
            "config": config_a,
            "score_json": str(score_a),
            "kospi_hit_rate": round(ha_tot / n, 4),
            "btc_lens_wf_mean": _gate_btc_lens_mean(gates_a) if gates_a else None,
        },
        label_b: {
            "config": config_b,
            "score_json": str(score_b),
            "kospi_hit_rate": round(hb_tot / n, 4),
            "btc_lens_wf_mean": _gate_btc_lens_mean(gates_b) if gates_b else None,
        },
        f"delta_{label_b}_minus_{label_a}_hit_rate": round((hb_tot - ha_tot) / n, 4),
        "pred_agreement": {
            "same_pred_days": agree_same_pred,
            "disagree_days": disagree,
            "disagree_rate": round(disagree / n, 4),
        },
        "disagreement_outcomes": {
            f"only_{label_a}_hit": only_a_hit,
            f"only_{label_b}_hit": only_b_hit,
            "both_hit_on_agree": both_hit,
            "both_miss_on_agree": both_miss,
        },
        "monthly_bands": month_table,
        "disagreement_days": disagree_days,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--label-a", default="ovn050")
    ap.add_argument("--score-a", type=Path, default=ROOT / "reports/btrack_score_leading_180d_v1_latest.json")
    ap.add_argument("--config-a", default="reports/kospi_ensemble_hypo_leading_candidate_v1.json")
    ap.add_argument("--gates-a", type=Path, default=ROOT / "reports/gates_leading_180d_v1_latest.json")
    ap.add_argument("--label-b", default="prlow035")
    ap.add_argument("--score-b", type=Path, default=ROOT / "reports/btrack_score_prlow035_180d_v1_latest.json")
    ap.add_argument("--config-b", default="reports/kospi_ensemble_hypo_prlow035_v1.json")
    ap.add_argument("--gates-b", type=Path, default=ROOT / "reports/gates_prlow035_180d_v1_latest.json")
    ap.add_argument("--output", type=Path, default=ROOT / "reports/kospi_ovn050_vs_prlow035_180d_compare_v1_latest.json")
    args = ap.parse_args(argv)

    doc = compare(
        label_a=args.label_a,
        score_a=args.score_a if args.score_a.is_absolute() else ROOT / args.score_a,
        config_a=args.config_a,
        gates_a=args.gates_a if args.gates_a.is_absolute() else ROOT / args.gates_a,
        label_b=args.label_b,
        score_b=args.score_b if args.score_b.is_absolute() else ROOT / args.score_b,
        config_b=args.config_b,
        gates_b=args.gates_b if args.gates_b.is_absolute() else ROOT / args.gates_b,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"{args.label_a}={doc[args.label_a]['kospi_hit_rate']} "
        f"{args.label_b}={doc[args.label_b]['kospi_hit_rate']} "
        f"delta={doc[f'delta_{args.label_b}_minus_{args.label_a}_hit_rate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
