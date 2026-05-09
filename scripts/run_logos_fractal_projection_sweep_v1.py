#!/usr/bin/env python3
"""Sweep projection-lexicon variants + SLKM weights for fractal fit."""

from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_MATRIX = ART / "logos_fractal_archetype_4d_matrix_v1.json"
DEFAULT_OUT = ART / "logos_fractal_projection_sweep_latest.json"


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


def _lexicon_variants(base: dict[str, list[str]]) -> list[dict[str, Any]]:
    def add(lex: dict[str, list[str]], key: str, vals: list[str]) -> None:
        cur = list(lex.get(key, []))
        for v in vals:
            if v not in cur:
                cur.append(v)
        lex[key] = cur

    out: list[dict[str, Any]] = [{"id": "baseline", "lex": deepcopy(base)}]

    v1 = deepcopy(base)
    add(v1, "K_positive", ["breakout", "regime shift", "disruption", "repricing"])
    add(v1, "M_negative", ["funding stress", "margin call", "liquidity crunch"])
    add(v1, "S_negative", ["moral hazard", "trust erosion"])
    out.append({"id": "macro_risk_heavy", "lex": v1})

    v2 = deepcopy(base)
    add(v2, "M_positive", ["risk-on", "carry", "multiple expansion"])
    add(v2, "M_negative", ["risk-off", "de-risking", "drawdown"])
    add(v2, "L_positive", ["coordination", "policy support"])
    out.append({"id": "liquidity_cycle", "lex": v2})

    v3 = deepcopy(base)
    add(v3, "L_positive", ["rule-of-law", "institutional credibility", "framework upgrade"])
    add(v3, "L_negative", ["policy vacuum", "institutional drift"])
    add(v3, "S_positive", ["confidence"])
    out.append({"id": "policy_order", "lex": v3})

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Run projection lexicon sweep.")
    ap.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    matrix = _load_json(args.matrix_json)
    base_lex = matrix.get("projection_lexicon") or {}
    archetypes = []
    for a in matrix.get("archetypes", []):
        vec = a.get("vector_slkm") or {}
        archetypes.append(
            {
                "id": str(a.get("id", "")),
                "vec": {
                    "S": float(vec.get("S", 0.5)),
                    "L": float(vec.get("L", 0.5)),
                    "K": float(vec.get("K", 0.5)),
                    "M": float(vec.get("M", 0.5)),
                },
            }
        )

    weight_candidates = [
        {"id": "balanced", "w": {"S": 1.0, "L": 1.0, "K": 1.0, "M": 1.0}},
        {"id": "material_heavy", "w": {"S": 0.994, "L": 0.508, "K": 0.957, "M": 1.48}},
        {"id": "anti_kairos", "w": {"S": 1.0, "L": 1.1, "K": 0.5, "M": 1.1}},
    ]

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

    perf_rows = []
    for tag in tags:
        bp = _tag_backtest_path(tag)
        np = _tag_news_path(tag)
        if not bp.exists() or not np.exists():
            continue
        bdoc = _load_json(bp)
        perf_rows.append(
            {
                "tag": tag,
                "news_path": np,
                "hit_rate": float((bdoc.get("summary") or {}).get("hit_rate") or 0.0),
                "non_synthetic_hit_rate": float((bdoc.get("summary") or {}).get("non_synthetic_hit_rate") or 0.0),
            }
        )

    variants = _lexicon_variants(base_lex)
    candidates: list[dict[str, Any]] = []
    for lv in variants:
        for wc in weight_candidates:
            x: list[float] = []
            y: list[float] = []
            y_ns: list[float] = []
            for pr in perf_rows:
                news = _load_jsonl(pr["news_path"])
                cur = _mean_vec([_project_text(str(r.get("canonical_text", "")), lv["lex"]) for r in news])
                best_res = -1.0
                for a in archetypes:
                    res = _weighted_cosine(cur, a["vec"], wc["w"])
                    if res > best_res:
                        best_res = res
                x.append(best_res)
                y.append(pr["hit_rate"])
                y_ns.append(pr["non_synthetic_hit_rate"])
            c_hr = _corr(x, y)
            c_ns = _corr(x, y_ns)
            candidates.append(
                {
                    "lexicon_variant_id": lv["id"],
                    "weight_id": wc["id"],
                    "weights_slkm": wc["w"],
                    "corr_resonance_vs_hit_rate": c_hr,
                    "corr_resonance_vs_non_synthetic_hit_rate": c_ns,
                    "objective": c_ns if c_ns is not None else -999.0,
                }
            )

    candidates.sort(key=lambda c: float(c["objective"]), reverse=True)
    out = {
        "schema": "logos_fractal_projection_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "input_run_count": len(perf_rows),
        "candidates_top10": candidates[:10],
        "best_candidate": candidates[0] if candidates else None,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "input_run_count": len(perf_rows), "best": out["best_candidate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

