#!/usr/bin/env python3
"""Search blended parameter ensembles for proxy profile D."""

from __future__ import annotations

import argparse
import itertools
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "BLIND_REPLAY_PROXY_PROFILE_D_ENSEMBLE_SEARCH_V1.json"
DEFAULT_CANON = ART / "BLIND_REPLAY_PROXY_PROFILE_D_PARAMS_V1.json"

REQUIRED = {
    "m_myeongni",
    "d_myeongni",
    "m_sasang",
    "d_sasang",
    "v_penalty",
    "m_logos",
    "r_bonus",
    "band_m",
    "band_s",
    "band_l",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _norm_label(v: Any) -> str:
    s = str(v or "").strip().upper()
    if s in {"DOWN", "BEAR", "DOWN_STRONG", "NEGATIVE"}:
        return "DOWN_STRONG"
    if s in {"UP", "BULL", "UP_STRONG", "POSITIVE"}:
        return "UP_STRONG"
    if s in {"NEUTRAL", "HOLD", "FLAT"}:
        return "NEUTRAL"
    return "UNKNOWN"


def _sign(score: float, band: float) -> str:
    if score <= -band:
        return "DOWN_STRONG"
    if score >= band:
        return "UP_STRONG"
    return "NEUTRAL"


def _weighted_sigma(values: dict[str, float], weights: dict[str, float]) -> float:
    total_w = sum(weights.values())
    if total_w <= 0:
        return 0.0
    mu = sum(weights[k] * values.get(k, 0.0) for k in weights) / total_w
    var = sum(weights[k] * ((values.get(k, 0.0) - mu) ** 2) for k in weights) / total_w
    return math.sqrt(max(0.0, var))


def _load_seed_runs(grid_path: Path) -> list[tuple[list[dict[str, Any]], dict[str, str]]]:
    grid = _read_json(grid_path)
    best_cfg = grid.get("best_config") if isinstance(grid.get("best_config"), dict) else {}
    runs = best_cfg.get("seed_runs") if isinstance(best_cfg.get("seed_runs"), list) else []
    out: list[tuple[list[dict[str, Any]], dict[str, str]]] = []
    for r in runs:
        pub = Path(str(r.get("public_dataset") or ""))
        key = Path(str(r.get("answer_key") or ""))
        public_rows = _read_jsonl(pub)
        key_rows = _read_jsonl(key)
        if not public_rows or not key_rows:
            continue
        truth = {str(x.get("sample_id") or ""): _norm_label(x.get("answer_label")) for x in key_rows}
        out.append((public_rows, truth))
    return out


def _eval_one_run(params: dict[str, float], public_rows: list[dict[str, Any]], truth: dict[str, str]) -> float:
    per_total = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}
    per_hit = {"DOWN_STRONG": 0, "UP_STRONG": 0, "NEUTRAL": 0}
    for r in public_rows:
        sid = str(r.get("sample_id") or "")
        t = truth.get(sid, "UNKNOWN")
        if t in per_total:
            per_total[t] += 1
        feat = r.get("features") if isinstance(r.get("features"), dict) else {}
        m = float(feat.get("momentum_index") or 0.0)
        v = float(feat.get("volatility_index") or 0.0)
        d = float(feat.get("drawdown_index") or 0.0)
        rp = float(feat.get("range_spread_index") or 0.0)
        sm = (params["m_myeongni"] * m) + (params["d_myeongni"] * d)
        ss = (params["m_sasang"] * m) + (params["d_sasang"] * d) - (params["v_penalty"] * max(0.0, v - 0.12))
        sl = (params["m_logos"] * m) + (params["r_bonus"] * (0.25 - min(0.25, abs(rp - 0.25))))
        vm = _sign(sm, params["band_m"])
        vs = _sign(ss, params["band_s"])
        vl = _sign(sl, params["band_l"])
        down = [vm, vs, vl].count("DOWN_STRONG")
        up = [vm, vs, vl].count("UP_STRONG")
        pred = "DOWN_STRONG" if down > up else ("UP_STRONG" if up > down else "NEUTRAL")
        if pred == t and t in per_hit:
            per_hit[t] += 1
    parts: list[float] = []
    for lbl in ("DOWN_STRONG", "UP_STRONG", "NEUTRAL"):
        if per_total[lbl] > 0:
            parts.append(per_hit[lbl] / per_total[lbl])
    return (sum(parts) / len(parts)) if parts else 0.0


def _blend(parts: list[dict[str, float]], ws: list[float]) -> dict[str, float]:
    total = sum(ws)
    if total <= 0:
        total = 1.0
    return {k: sum(w * p[k] for w, p in zip(ws, parts)) / total for k in REQUIRED}


def _extract_params(path: Path, limit_top: int) -> list[dict[str, float]]:
    doc = _read_json(path)
    out: list[dict[str, float]] = []
    best = doc.get("best") if isinstance(doc.get("best"), dict) else {}
    bp = best.get("params") if isinstance(best.get("params"), dict) else {}
    if REQUIRED.issubset(set(bp.keys())):
        out.append({k: float(bp[k]) for k in REQUIRED})
    top = doc.get("top20") if isinstance(doc.get("top20"), list) else []
    for row in top[: max(0, int(limit_top))]:
        rp = row.get("params") if isinstance(row, dict) else {}
        if isinstance(rp, dict) and REQUIRED.issubset(set(rp.keys())):
            out.append({k: float(rp[k]) for k in REQUIRED})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Search blended D-params ensembles from top candidates.")
    ap.add_argument("--btc-grid", type=Path, required=True)
    ap.add_argument("--kospi-grid", type=Path, required=True)
    ap.add_argument("--candidates", required=True, help="Comma-separated tuning artifact json paths")
    ap.add_argument("--limit-top-per-file", type=int, default=8)
    ap.add_argument("--w-btc", type=float, default=0.7)
    ap.add_argument("--w-kospi", type=float, default=0.3)
    ap.add_argument("--kappa", type=float, default=0.15)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--canonical", type=Path, default=DEFAULT_CANON)
    ap.add_argument("--promote-if-better", action="store_true")
    args = ap.parse_args()

    btc_runs = _load_seed_runs(args.btc_grid)
    kospi_runs = _load_seed_runs(args.kospi_grid)
    if not btc_runs or not kospi_runs:
        raise SystemExit("No seed runs loaded from grids")

    candidate_paths = [Path(x.strip()) for x in str(args.candidates).split(",") if x.strip()]
    pool: list[dict[str, float]] = []
    for p in candidate_paths:
        pool.extend(_extract_params(p, args.limit_top_per_file))
    # de-duplicate by rounded tuple
    seen = set()
    uniq: list[dict[str, float]] = []
    for d in pool:
        key = tuple(round(float(d[k]), 6) for k in sorted(REQUIRED))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(d)
    if len(uniq) < 2:
        raise SystemExit("Need at least 2 unique parameter candidates")

    weights = {"BTC": float(args.w_btc), "KOSPI": float(args.w_kospi)}
    base_doc = _read_json(args.canonical)
    base_best = float(((base_doc.get("best") or {}).get("unified_score_balanced") or 0.0))

    trials: list[dict[str, Any]] = []
    idxs = list(range(len(uniq)))
    alpha2 = [0.25, 0.5, 0.75]
    alpha3 = [0.2, 0.3, 0.5]

    # 2-way blends
    for i, j in itertools.combinations(idxs, 2):
        p1, p2 = uniq[i], uniq[j]
        for a in alpha2:
            b = 1.0 - a
            params = _blend([p1, p2], [a, b])
            btc_bal = sum(_eval_one_run(params, pub, truth) for pub, truth in btc_runs) / len(btc_runs)
            kospi_bal = sum(_eval_one_run(params, pub, truth) for pub, truth in kospi_runs) / len(kospi_runs)
            mu = (weights["BTC"] * btc_bal + weights["KOSPI"] * kospi_bal) / (weights["BTC"] + weights["KOSPI"])
            sigma = _weighted_sigma({"BTC": btc_bal, "KOSPI": kospi_bal}, weights)
            score = mu - float(args.kappa) * sigma
            trials.append(
                {
                    "kind": "blend2",
                    "members": [i, j],
                    "weights": [round(a, 4), round(b, 4)],
                    "params": {k: round(params[k], 6) for k in REQUIRED},
                    "btc_balanced_accuracy_mean": round(btc_bal, 6),
                    "kospi_balanced_accuracy_mean": round(kospi_bal, 6),
                    "unified_score_balanced": round(score, 6),
                }
            )

    # 3-way blends (limited patterns)
    for i, j, k in itertools.combinations(idxs, 3):
        p1, p2, p3 = uniq[i], uniq[j], uniq[k]
        for ws in ([1 / 3, 1 / 3, 1 / 3], alpha3, [alpha3[1], alpha3[2], alpha3[0]]):
            params = _blend([p1, p2, p3], ws)
            btc_bal = sum(_eval_one_run(params, pub, truth) for pub, truth in btc_runs) / len(btc_runs)
            kospi_bal = sum(_eval_one_run(params, pub, truth) for pub, truth in kospi_runs) / len(kospi_runs)
            mu = (weights["BTC"] * btc_bal + weights["KOSPI"] * kospi_bal) / (weights["BTC"] + weights["KOSPI"])
            sigma = _weighted_sigma({"BTC": btc_bal, "KOSPI": kospi_bal}, weights)
            score = mu - float(args.kappa) * sigma
            trials.append(
                {
                    "kind": "blend3",
                    "members": [i, j, k],
                    "weights": [round(float(x), 4) for x in ws],
                    "params": {k0: round(params[k0], 6) for k0 in REQUIRED},
                    "btc_balanced_accuracy_mean": round(btc_bal, 6),
                    "kospi_balanced_accuracy_mean": round(kospi_bal, 6),
                    "unified_score_balanced": round(score, 6),
                }
            )

    trials.sort(key=lambda x: float(x["unified_score_balanced"]), reverse=True)
    best = trials[0]
    payload = {
        "schema": "blind_replay_proxy_profile_d_ensemble_search_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "inputs": {
            "btc_grid": str(args.btc_grid.resolve()),
            "kospi_grid": str(args.kospi_grid.resolve()),
            "candidate_artifacts": [str(x.resolve()) for x in candidate_paths],
            "candidate_count_unique": len(uniq),
        },
        "objective": {"w_btc": float(args.w_btc), "w_kospi": float(args.w_kospi), "kappa": float(args.kappa)},
        "baseline_canonical_best": round(base_best, 6),
        "best": best,
        "top20": trials[:20],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    promoted = False
    if args.promote_if_better and float(best["unified_score_balanced"]) > base_best:
        canon = base_doc if isinstance(base_doc, dict) else {}
        canon["generated_at_utc"] = _utc_now()
        canon["best"] = {
            "iter": -1,
            "params": best["params"],
            "btc_balanced_accuracy_mean": best["btc_balanced_accuracy_mean"],
            "kospi_balanced_accuracy_mean": best["kospi_balanced_accuracy_mean"],
            "unified_score_balanced": best["unified_score_balanced"],
            "mu_balanced": best["unified_score_balanced"],
            "sigma_balanced": 0.0,
        }
        canon["note"] = "Promoted from ensemble blend search."
        args.canonical.parent.mkdir(parents=True, exist_ok=True)
        args.canonical.write_text(json.dumps(canon, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        promoted = True

    print(f"WROTE: {args.out.resolve()}")
    print(f"BEST unified_score_balanced={best['unified_score_balanced']}")
    print(f"PROMOTED={str(promoted).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

