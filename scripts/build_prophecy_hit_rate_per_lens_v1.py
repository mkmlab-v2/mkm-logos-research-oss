#!/usr/bin/env python3
"""Build prophecy_hit_rate_per_lens_latest.json (B-track, research_only).

Compares each lens's *latest snapshot* implied direction vs realized daily directions
from ``btrack_prophecy_score_v1`` rows (KOSPI/BTC legs). Same frozen-direction methodology
as the OHLCV score builder: each lens direction is held constant across all eval_date
rows in the score file (counterfactual leaderboard).

Does not auto-apply weights or touch live trading.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "prophecy_hit_rate_per_lens_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _confidence_band(n: int) -> str:
    if n < 20:
        return "low"
    if n < 100:
        return "medium"
    return "high"


def _score_to_direction(score: float, neutral_abs: float) -> str:
    if score > neutral_abs:
        return "bull"
    if score < -neutral_abs:
        return "bear"
    return "neutral"


def _resolve_workspace(p: str) -> Path:
    return Path(p).expanduser().resolve()


def _rel(root: Path, p: Path) -> str:
    try:
        return str(p.resolve().relative_to(root))
    except ValueError:
        return str(p)


def _collect_lens_predictions(
    *,
    root: Path,
    hypothesis: dict[str, Any],
    fusion: dict[str, Any] | None,
    neutral_abs: float,
) -> list[dict[str, Any]]:
    """Return list of {lens_id, predicted_direction, source, detail}."""
    out: list[dict[str, Any]] = []

    if fusion and isinstance(fusion.get("inputs"), list):
        for item in fusion["inputs"]:
            if not isinstance(item, dict):
                continue
            if not item.get("available"):
                continue
            lid = str(item.get("lens_id") or "").strip()
            if not lid:
                continue
            veto = bool((item.get("market_sasang_lens_v1") or {}).get("veto_force_hold"))
            if veto:
                pred = "neutral"
                detail = "market_sasang veto_force_hold -> neutral for scoring"
            else:
                sign = str(item.get("direction_sign") or "").strip().lower()
                if sign in ("bull", "bear", "neutral"):
                    pred = sign
                    detail = "fusion_stub direction_sign"
                else:
                    ds = item.get("direction_score")
                    pred = (
                        _score_to_direction(float(ds), neutral_abs)
                        if isinstance(ds, (int, float))
                        else "neutral"
                    )
                    detail = "direction_sign missing; derived from direction_score"
            out.append(
                {
                    "lens_id": lid,
                    "predicted_direction": pred,
                    "source": "independent_lens_fusion_stub_latest.json",
                    "detail": detail,
                    "lens_confidence_snapshot": item.get("confidence"),
                }
            )

    rt = hypothesis.get("runtime_meta") or {}
    lv = rt.get("lens_values") or {}
    if isinstance(lv, dict):
        for key in ("price", "macro", "news"):
            block = lv.get(key)
            if not isinstance(block, dict):
                continue
            sc = block.get("score")
            if not isinstance(sc, (int, float)):
                continue
            pred = _score_to_direction(float(sc), neutral_abs)
            conf = block.get("confidence")
            out.append(
                {
                    "lens_id": key,
                    "predicted_direction": pred,
                    "source": "btrack_hypothesis_prophecy_latest.json:runtime_meta.lens_values",
                    "detail": "score-derived",
                    "lens_confidence_snapshot": conf if isinstance(conf, (int, float)) else None,
                }
            )

    pred_block = hypothesis.get("prediction") or {}
    ens = str(pred_block.get("direction") or "").strip().lower()
    if ens in ("bull", "bear", "neutral"):
        out.append(
            {
                "lens_id": "ensemble_hypothesis",
                "predicted_direction": ens,
                "source": "btrack_hypothesis_prophecy_latest.json:prediction.direction",
                "detail": "frozen ensemble direction (same as eval score builder hypothesis)",
                "lens_confidence_snapshot": pred_block.get("confidence")
                if isinstance(pred_block.get("confidence"), (int, float))
                else None,
            }
        )

    return out


def _global_regime_tag(hypothesis: dict[str, Any], root: Path) -> str:
    arts = hypothesis.get("lens_artifacts") or {}
    p = arts.get("sasang")
    if not isinstance(p, str) or not p.strip():
        return "unknown"
    doc = _load_json((root / p).resolve())
    if not doc:
        return "unknown"
    so = doc.get("sasang_stream_outputs") or {}
    tag = str(so.get("regime_hypothesis") or "").strip()
    return tag or "unknown"


def _eval_leg(
    *,
    rows: list[dict[str, Any]],
    instrument: str,
    lens_id: str,
    predicted: str,
) -> dict[str, Any]:
    hits = 0
    n = 0
    for r in rows:
        if str(r.get("instrument") or "") != instrument:
            continue
        ad = str(r.get("actual_direction") or "").strip().lower()
        pd = predicted
        if pd not in ("bull", "bear", "neutral") or ad not in ("bull", "bear", "neutral"):
            continue
        n += 1
        if pd == ad:
            hits += 1
    rate = round(hits / n, 6) if n else None
    return {
        "lens_id": lens_id,
        "instrument": instrument,
        "predicted_direction": predicted,
        "price_directional_hit_rate": rate,
        "n_evaluated": n,
        "price_hits": hits,
        "confidence_band": _confidence_band(n),
        "calibration": None,
        "calibration_note": "Snapshot lens directions only; no per-date probability path for Brier/ECE in v1.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument(
        "--score-json",
        type=Path,
        default=None,
        help="btrack_prophecy_score_v1 JSON (default: docs/final/artifacts/btrack_prophecy_score_latest.json)",
    )
    ap.add_argument(
        "--hypothesis-json",
        type=Path,
        default=None,
        help="btrack hypothesis JSON (default: docs/final/artifacts/btrack_hypothesis_prophecy_latest.json)",
    )
    ap.add_argument(
        "--fusion-json",
        type=Path,
        default=None,
        help="fusion stub JSON (default: docs/final/artifacts/independent_lens_fusion_stub_latest.json)",
    )
    ap.add_argument(
        "--neutral-score-abs",
        type=float,
        default=0.05,
        help="If fusion input lacks direction_sign, map direction_score to bull/bear/neutral using this abs threshold.",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: docs/final/artifacts/prophecy_hit_rate_per_lens_latest.json)",
    )
    ns = ap.parse_args()
    root = _resolve_workspace(str(ns.workspace_root))
    score_path = ns.score_json or (root / "docs/final/artifacts/btrack_prophecy_score_latest.json")
    hyp_path = ns.hypothesis_json or (root / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json")
    fusion_path = ns.fusion_json or (root / "docs/final/artifacts/independent_lens_fusion_stub_latest.json")
    out_path = ns.output or (root / "docs/final/artifacts/prophecy_hit_rate_per_lens_latest.json")

    score_doc = _load_json(score_path)
    if not score_doc or not isinstance(score_doc.get("rows"), list):
        print(f"ERROR: invalid score json: {score_path}", file=__import__("sys").stderr)
        return 2
    rows = [r for r in score_doc["rows"] if isinstance(r, dict)]
    instruments = sorted({str(r.get("instrument") or "") for r in rows if r.get("instrument")})

    hypothesis = _load_json(hyp_path)
    if not hypothesis:
        print(f"ERROR: invalid hypothesis json: {hyp_path}", file=__import__("sys").stderr)
        return 2
    fusion = _load_json(fusion_path)

    lens_preds = _collect_lens_predictions(
        root=root,
        hypothesis=hypothesis,
        fusion=fusion,
        neutral_abs=float(ns.neutral_score_abs),
    )
    regime_tag = _global_regime_tag(hypothesis, root)

    legs_out: dict[str, Any] = {}
    for inst in instruments:
        lens_rows: list[dict[str, Any]] = []
        for lp in lens_preds:
            lid = str(lp["lens_id"])
            pred = str(lp["predicted_direction"])
            row = _eval_leg(rows=rows, instrument=inst, lens_id=lid, predicted=pred)
            row["regime_tag"] = regime_tag
            row["lens_confidence_snapshot"] = lp.get("lens_confidence_snapshot")
            row["prediction_source"] = lp.get("source")
            row["prediction_detail"] = lp.get("detail")
            lens_rows.append(row)
        legs_out[inst] = {"lenses": lens_rows}

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "zeroing_note": "Per-lens directions are latest snapshot signals held constant across score rows (counterfactual).",
        "window": {
            "recent_trading_days": (score_doc.get("inputs") or {}).get("recent_trading_days"),
            "batch_eval_dates": (score_doc.get("meta") or {}).get("batch_eval_dates"),
            "instruments_observed": instruments,
        },
        "inputs": {
            "score_json": _rel(root, score_path),
            "hypothesis_json": _rel(root, hyp_path),
            "fusion_json": _rel(root, fusion_path) if fusion and fusion_path.is_file() else None,
            "neutral_score_abs": float(ns.neutral_score_abs),
            "global_regime_tag": regime_tag,
        },
        "legs": legs_out,
        "sources": {
            "score_json": _rel(root, score_path),
            "hypothesis_json": _rel(root, hyp_path),
            "fusion_json": _rel(root, fusion_path) if fusion_path.is_file() else None,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
