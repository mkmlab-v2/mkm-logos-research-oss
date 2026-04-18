# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.82, K:0.55, M:0.7}
# Balance: 86
# Purpose: Observation-only agreement between independent-lens direction_score sign and score row directions (no promotion).
# Keywords: btrack, sidecar, lens, hit-rate, observation
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_SIDECAR = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_insight_sidecar_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_insight_sidecar_lens_hit_agreement_v1_latest.json"

SCHEMA = "btrack_insight_sidecar_lens_hit_agreement_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _direction_from_score(value: Any) -> str | None:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if x > 0.0:
        return "bull"
    if x < 0.0:
        return "bear"
    return "neutral"


def _agree_counts(
    score_rows: list[dict[str, Any]],
    per_date: list[dict[str, Any]],
    lens_key: str,
    instrument_filter: str | None,
) -> dict[str, Any]:
    actual_hits = 0
    pred_hits = 0
    n = 0
    skipped_no_lens = 0
    for i, srow in enumerate(score_rows):
        if i >= len(per_date):
            break
        ins = str(srow.get("instrument") or "").strip().lower()
        if instrument_filter and ins != instrument_filter:
            continue
        act = str(srow.get("actual_direction") or "").strip().lower()
        pred = str(srow.get("predicted_direction") or "").strip().lower()
        if act not in ("bull", "bear", "neutral") or pred not in ("bull", "bear", "neutral"):
            continue
        snap = per_date[i].get("lens_scores_snapshot")
        if not isinstance(snap, dict):
            skipped_no_lens += 1
            continue
        block = snap.get(lens_key)
        if not isinstance(block, dict):
            skipped_no_lens += 1
            continue
        ldir = _direction_from_score(block.get("direction_score"))
        if ldir is None:
            skipped_no_lens += 1
            continue
        n += 1
        if ldir == act:
            actual_hits += 1
        if ldir == pred:
            pred_hits += 1
    return {
        "rows_used": n,
        "skipped_no_lens_direction": skipped_no_lens,
        "agree_with_actual": actual_hits,
        "agree_with_predicted": pred_hits,
        "rate_agree_with_actual": (actual_hits / n) if n else None,
        "rate_agree_with_predicted": (pred_hits / n) if n else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--instrument",
        choices=("kospi", "btc", "all"),
        default="all",
        help="Restrict score rows by instrument (default all).",
    )
    args = ap.parse_args()

    score = _load(args.score_json)
    side = _load(args.sidecar_json)
    rows = score.get("rows") if isinstance(score.get("rows"), list) else []
    score_rows = [x for x in rows if isinstance(x, dict)]
    pdf = side.get("per_date_features")
    per_date = pdf if isinstance(pdf, list) else []

    warnings: list[str] = []
    if not per_date:
        warnings.append("per_date_features_missing_or_empty")
    if len(per_date) != len(score_rows):
        warnings.append(f"per_date_len_mismatch_score_rows:{len(per_date)}_vs_{len(score_rows)}")

    inst_f: str | None = None if args.instrument == "all" else args.instrument

    by_lens: dict[str, Any] = {}
    for lk in ("logos", "myeongni", "sasang"):
        by_lens[lk] = _agree_counts(score_rows, per_date, lk, inst_f)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "instrument_filter": args.instrument,
        "paired_score_ref": _rel(args.score_json),
        "sidecar_ref": _rel(args.sidecar_json),
        "score_row_count": len(score_rows),
        "per_date_feature_count": len(per_date),
        "by_lens": by_lens,
        "warnings": warnings,
        "notes_ko": [
            "렌즈 direction_score 부호→bull/bear/neutral 규칙은 사이드카 빌더와 동일 해석(관측).",
            "적중 정의는 actual_direction / predicted_direction과의 문자열 일치만; 승격 게이트 미사용.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
