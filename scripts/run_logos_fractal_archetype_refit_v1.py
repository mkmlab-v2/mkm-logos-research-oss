#!/usr/bin/env python3
"""Refit archetype SLKM vectors by random search (B-track research only)."""

from __future__ import annotations

import argparse
import json
import math
import random
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_MATRIX = ART / "logos_fractal_archetype_4d_matrix_v1.json"
DEFAULT_OUT = ART / "logos_fractal_archetype_refit_latest.json"


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


def _tag_news_path(tag: str) -> Path:
    if tag == "latest":
        return ART / "news_observation_v1_latest.jsonl"
    if tag == "contrastive_challenge":
        return ART / "news_observation_v1_contrastive_challenge_latest.jsonl"
    if tag == "contrastive_expanded":
        return ART / "news_observation_v1_contrastive_challenge_expanded_latest.jsonl"
    if tag == "split1":
        return ART / "news_observation_v1_contrastive_challenge_split1_latest.jsonl"
    if tag == "split2":
        return ART / "news_observation_v1_contrastive_challenge_split2_latest.jsonl"
    if tag == "split3":
        return ART / "news_observation_v1_contrastive_challenge_split3_latest.jsonl"
    if tag == "blind_split":
        return ART / "news_observation_v1_blind_split_latest.jsonl"
    if tag == "blind_split_hardset":
        return ART / "news_observation_v1_blind_split_hardset_latest.jsonl"
    raise ValueError(tag)


def _tag_backtest_path(tag: str) -> Path:
    if tag == "latest":
        return ART / "logos_symbolic_event_backtest_latest_latest.json"
    return ART / f"logos_symbolic_event_backtest_{tag}_latest.json"


def _mutate_vec(rng: random.Random, vec: dict[str, float], sigma: float = 0.18) -> dict[str, float]:
    out = {}
    for d in ("S", "L", "K", "M"):
        v = float(vec[d]) + rng.uniform(-sigma, sigma)
        out[d] = max(0.0, min(1.0, round(v, 6)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Refit archetype vectors by random search.")
    ap.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--iterations", type=int, default=400)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    matrix = _load_json(args.matrix_json)
    base_archetypes = deepcopy(matrix.get("archetypes") or [])
    lex = matrix.get("projection_lexicon") or {}
    weights = {"S": 0.994, "L": 0.508, "K": 0.957, "M": 1.48}  # best-so-far sweep result

    tags = [
        "latest",
        "contrastive_challenge",
        "contrastive_expanded",
        "split1",
        "split2",
        "split3",
        "blind_split",
        "blind_split_hardset",
    ]
    rows = []
    for t in tags:
        np = _tag_news_path(t)
        bp = _tag_backtest_path(t)
        if not np.exists() or not bp.exists():
            continue
        news = _load_jsonl(np)
        cur = _mean_vec([_project_text(str(r.get("canonical_text", "")), lex) for r in news])
        bdoc = _load_json(bp)
        summ = bdoc.get("summary") or {}
        rows.append(
            {
                "tag": t,
                "current_vec": cur,
                "hit_rate": float(summ.get("hit_rate") or 0.0),
                "non_synthetic_hit_rate": float(summ.get("non_synthetic_hit_rate") or 0.0),
            }
        )

    def eval_objective(arch_list: list[dict[str, Any]]) -> tuple[float | None, float | None]:
        x: list[float] = []
        y_hr: list[float] = []
        y_ns: list[float] = []
        for r in rows:
            best = -1.0
            for a in arch_list:
                v = a.get("vector_slkm") or {}
                arche = {
                    "S": float(v.get("S", 0.5)),
                    "L": float(v.get("L", 0.5)),
                    "K": float(v.get("K", 0.5)),
                    "M": float(v.get("M", 0.5)),
                }
                res = _weighted_cosine(r["current_vec"], arche, weights)
                if res > best:
                    best = res
            x.append(best)
            y_hr.append(float(r["hit_rate"]))
            y_ns.append(float(r["non_synthetic_hit_rate"]))
        return _corr(x, y_hr), _corr(x, y_ns)

    base_corr_hr, base_corr_ns = eval_objective(base_archetypes)
    rng = random.Random(args.seed)
    best = deepcopy(base_archetypes)
    best_hr, best_ns = base_corr_hr, base_corr_ns
    trials: list[dict[str, Any]] = []

    for i in range(max(1, int(args.iterations))):
        cand = deepcopy(best)
        idx = rng.randrange(0, len(cand))
        vec = cand[idx].get("vector_slkm") or {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5}
        cand[idx]["vector_slkm"] = _mutate_vec(rng, vec, sigma=0.2)
        c_hr, c_ns = eval_objective(cand)
        obj_best = -999.0 if best_ns is None else float(best_ns)
        obj_new = -999.0 if c_ns is None else float(c_ns)
        if obj_new > obj_best:
            best = cand
            best_hr, best_ns = c_hr, c_ns
        if i < 50 or i % 50 == 0:
            trials.append(
                {
                    "iter": i + 1,
                    "corr_resonance_vs_hit_rate": c_hr,
                    "corr_resonance_vs_non_synthetic_hit_rate": c_ns,
                }
            )

    out = {
        "schema": "logos_fractal_archetype_refit_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "search_meta": {
            "iterations": int(args.iterations),
            "seed": int(args.seed),
            "input_run_count": len(rows),
            "weights_slkm_fixed": weights,
        },
        "baseline": {
            "corr_resonance_vs_hit_rate": base_corr_hr,
            "corr_resonance_vs_non_synthetic_hit_rate": base_corr_ns,
        },
        "best": {
            "corr_resonance_vs_hit_rate": best_hr,
            "corr_resonance_vs_non_synthetic_hit_rate": best_ns,
            "archetypes": best,
        },
        "trials_sample": trials,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "baseline": out["baseline"],
                "best": {
                    "corr_resonance_vs_hit_rate": best_hr,
                    "corr_resonance_vs_non_synthetic_hit_rate": best_ns,
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

