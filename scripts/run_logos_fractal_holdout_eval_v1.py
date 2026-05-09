#!/usr/bin/env python3
"""Evaluate baseline vs refit candidate matrix on holdout-focused splits only."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_BASE_MATRIX = ART / "logos_fractal_archetype_4d_matrix_v1.json"
DEFAULT_CAND_MATRIX = ART / "logos_fractal_archetype_4d_matrix_refit_candidate_v1.json"
DEFAULT_OUT = ART / "logos_fractal_holdout_eval_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0.0 or den_y == 0.0:
        return None
    return round(num / (den_x * den_y), 6)


def _score_dim(text: str, pos: list[str], neg: list[str]) -> float:
    p = sum(1 for t in pos if t in text)
    n = sum(1 for t in neg if t in text)
    raw = 0.5 + 0.1 * (p - n)
    return max(0.0, min(1.0, raw))


def _project_text(text: str, lex: dict[str, list[str]]) -> dict[str, float]:
    t = text.lower()
    return {
        "S": _score_dim(t, lex.get("S_positive", []), lex.get("S_negative", [])),
        "L": _score_dim(t, lex.get("L_positive", []), lex.get("L_negative", [])),
        "K": _score_dim(t, lex.get("K_positive", []), lex.get("K_negative", [])),
        "M": _score_dim(t, lex.get("M_positive", []), lex.get("M_negative", [])),
    }


def _mean_vec(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5}
    n = float(len(rows))
    return {
        "S": sum(r["S"] for r in rows) / n,
        "L": sum(r["L"] for r in rows) / n,
        "K": sum(r["K"] for r in rows) / n,
        "M": sum(r["M"] for r in rows) / n,
    }


def _weighted_cosine(a: dict[str, float], b: dict[str, float], w: dict[str, float]) -> float:
    dims = ("S", "L", "K", "M")
    dot = sum(w[d] * a[d] * b[d] for d in dims)
    na = math.sqrt(sum(w[d] * a[d] * a[d] for d in dims))
    nb = math.sqrt(sum(w[d] * b[d] * b[d] for d in dims))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _eval_on_rows(rows: list[dict[str, Any]], matrix: dict[str, Any], weights: dict[str, float]) -> dict[str, Any]:
    arches = []
    for a in matrix.get("archetypes", []):
        v = a.get("vector_slkm") or {}
        arches.append({"id": str(a.get("id", "")), "vec": {"S": float(v.get("S", 0.5)), "L": float(v.get("L", 0.5)), "K": float(v.get("K", 0.5)), "M": float(v.get("M", 0.5))}})
    x: list[float] = []
    y_hr: list[float] = []
    y_ns: list[float] = []
    detail: list[dict[str, Any]] = []
    for r in rows:
        best = -1.0
        best_id = "unknown"
        for a in arches:
            res = _weighted_cosine(r["cur"], a["vec"], weights)
            if res > best:
                best = res
                best_id = a["id"]
        x.append(best)
        y_hr.append(r["hit_rate"])
        y_ns.append(r["non_synthetic_hit_rate"])
        detail.append({"tag": r["tag"], "top_archetype": best_id, "resonance_cosine": round(best, 6), "hit_rate": r["hit_rate"], "non_synthetic_hit_rate": r["non_synthetic_hit_rate"]})
    return {
        "corr_resonance_vs_hit_rate": _corr(x, y_hr),
        "corr_resonance_vs_non_synthetic_hit_rate": _corr(x, y_ns),
        "rows": detail,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Holdout eval for fractal candidate matrix.")
    ap.add_argument("--base-matrix-json", type=Path, default=DEFAULT_BASE_MATRIX)
    ap.add_argument("--candidate-matrix-json", type=Path, default=DEFAULT_CAND_MATRIX)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    base = _load_json(args.base_matrix_json)
    cand = _load_json(args.candidate_matrix_json)
    lex = base.get("projection_lexicon") or {}
    weights = {"S": 0.994, "L": 0.508, "K": 0.957, "M": 1.48}

    holdout_tags = ["split1", "split2", "split3", "blind_split_hardset"]
    rows: list[dict[str, Any]] = []
    for t in holdout_tags:
        news_path = (
            ART / f"news_observation_v1_contrastive_challenge_{t}_latest.jsonl"
            if t.startswith("split")
            else ART / "news_observation_v1_blind_split_hardset_latest.jsonl"
        )
        bt_path = ART / f"logos_symbolic_event_backtest_{t}_latest.json"
        if not news_path.exists() or not bt_path.exists():
            continue
        news = _load_jsonl(news_path)
        cur = _mean_vec([_project_text(str(n.get("canonical_text", "")), lex) for n in news])
        summ = (_load_json(bt_path).get("summary") or {})
        rows.append(
            {
                "tag": t,
                "cur": cur,
                "hit_rate": float(summ.get("hit_rate") or 0.0),
                "non_synthetic_hit_rate": float(summ.get("non_synthetic_hit_rate") or 0.0),
            }
        )

    base_eval = _eval_on_rows(rows, base, weights)
    cand_eval = _eval_on_rows(rows, cand, weights)
    out = {
        "schema": "logos_fractal_holdout_eval_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "weights_slkm": weights,
        "holdout_tag_count": len(rows),
        "baseline_eval": base_eval,
        "candidate_eval": cand_eval,
        "delta_non_synthetic_corr": (
            None
            if base_eval["corr_resonance_vs_non_synthetic_hit_rate"] is None
            or cand_eval["corr_resonance_vs_non_synthetic_hit_rate"] is None
            else round(
                float(cand_eval["corr_resonance_vs_non_synthetic_hit_rate"])
                - float(base_eval["corr_resonance_vs_non_synthetic_hit_rate"]),
                6,
            )
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "holdout_tag_count": len(rows),
                "baseline_corr_ns": base_eval["corr_resonance_vs_non_synthetic_hit_rate"],
                "candidate_corr_ns": cand_eval["corr_resonance_vs_non_synthetic_hit_rate"],
                "delta_non_synthetic_corr": out["delta_non_synthetic_corr"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

