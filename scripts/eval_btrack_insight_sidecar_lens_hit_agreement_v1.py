# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.72, L:0.84, K:0.56, M:0.72}
# Balance: 87
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
FORMAT_VERSION = "1.2.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _direction_from_mapping_target(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("bull", "long"):
        return "bull"
    if s in ("bear", "short"):
        return "bear"
    if s in ("sideways", "neutral", "flat"):
        return "neutral"
    if s in ("abstain", "", "none", "unknown"):
        return None
    return None


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


def _per_date_by_row_index(per_date: list[dict[str, Any]]) -> tuple[dict[int, dict[str, Any]], list[str]]:
    """Map score row index -> sidecar per_date row; prefer paired_row_index when valid."""
    warnings: list[str] = []
    out: dict[int, dict[str, Any]] = {}
    seen_dup: set[int] = set()
    for j, prow in enumerate(per_date):
        if not isinstance(prow, dict):
            continue
        raw_idx = prow.get("paired_row_index")
        if isinstance(raw_idx, int) and raw_idx >= 0:
            idx = raw_idx
        else:
            idx = j
            if raw_idx is not None:
                warnings.append(f"invalid_paired_row_index_at_sidecar_pos_{j}")
        if idx in out and idx not in seen_dup:
            seen_dup.add(idx)
            warnings.append(f"duplicate_paired_row_index:{idx}")
        out[idx] = prow
    return out, warnings


def _agree_counts(
    score_rows: list[dict[str, Any]],
    per_by_idx: dict[int, dict[str, Any]],
    lens_key: str,
    instrument_filter: str | None,
) -> dict[str, Any]:
    actual_hits = 0
    pred_hits = 0
    n = 0
    skipped_no_lens = 0
    skipped_no_sidecar_row = 0
    for i, srow in enumerate(score_rows):
        ins = str(srow.get("instrument") or "").strip().lower()
        if instrument_filter and ins != instrument_filter:
            continue
        act = str(srow.get("actual_direction") or "").strip().lower()
        pred = str(srow.get("predicted_direction") or "").strip().lower()
        if act not in ("bull", "bear", "neutral") or pred not in ("bull", "bear", "neutral"):
            continue
        prow = per_by_idx.get(i)
        if not isinstance(prow, dict):
            skipped_no_sidecar_row += 1
            continue
        snap = prow.get("lens_scores_snapshot")
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
        "skipped_no_sidecar_row": skipped_no_sidecar_row,
        "skipped_no_lens_direction": skipped_no_lens,
        "agree_with_actual": actual_hits,
        "agree_with_predicted": pred_hits,
        "rate_agree_with_actual": (actual_hits / n) if n else None,
        "rate_agree_with_predicted": (pred_hits / n) if n else None,
    }


def _agree_dated_aux_mapping_target(
    score_rows: list[dict[str, Any]],
    per_by_idx: dict[int, dict[str, Any]],
    dated_key: str,
    instrument_filter: str | None,
) -> dict[str, Any]:
    """Compare mapping_target from dated JSONL snapshot vs score row directions (observation)."""
    actual_hits = 0
    pred_hits = 0
    n = 0
    skipped_no_dated_block = 0
    skipped_no_aux = 0
    skipped_no_mapping_target = 0
    for i, srow in enumerate(score_rows):
        ins = str(srow.get("instrument") or "").strip().lower()
        if instrument_filter and ins != instrument_filter:
            continue
        act = str(srow.get("actual_direction") or "").strip().lower()
        pred = str(srow.get("predicted_direction") or "").strip().lower()
        if act not in ("bull", "bear", "neutral") or pred not in ("bull", "bear", "neutral"):
            continue
        prow = per_by_idx.get(i)
        if not isinstance(prow, dict):
            skipped_no_dated_block += 1
            continue
        dated_root = prow.get("dated_source_snapshots_asof_eval_date")
        if not isinstance(dated_root, dict):
            skipped_no_dated_block += 1
            continue
        aux = dated_root.get(dated_key)
        if not isinstance(aux, dict):
            skipped_no_aux += 1
            continue
        snap = aux.get("snapshot")
        if not isinstance(snap, dict):
            skipped_no_aux += 1
            continue
        mt = snap.get("mapping_target")
        ddir = _direction_from_mapping_target(mt)
        if ddir is None:
            skipped_no_mapping_target += 1
            continue
        n += 1
        if ddir == act:
            actual_hits += 1
        if ddir == pred:
            pred_hits += 1
    return {
        "rows_used": n,
        "skipped_no_dated_block": skipped_no_dated_block,
        "skipped_no_aux_row": skipped_no_aux,
        "skipped_no_mapping_target": skipped_no_mapping_target,
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
        help="Primary slice for top-level by_lens (default all). by_instrument always includes all three.",
    )
    args = ap.parse_args()

    score = _load(args.score_json)
    side = _load(args.sidecar_json)
    rows = score.get("rows") if isinstance(score.get("rows"), list) else []
    score_rows = [x for x in rows if isinstance(x, dict)]
    pdf = side.get("per_date_features")
    per_date = [x for x in pdf if isinstance(x, dict)] if isinstance(pdf, list) else []

    warnings: list[str] = []
    if not per_date:
        warnings.append("per_date_features_missing_or_empty")
    if len(per_date) != len(score_rows):
        warnings.append(f"per_date_len_mismatch_score_rows:{len(per_date)}_vs_{len(score_rows)}")

    per_by_idx, idx_warnings = _per_date_by_row_index(per_date)
    warnings.extend(idx_warnings)

    expected = set(range(len(score_rows)))
    got = set(per_by_idx.keys())
    if expected and not got.issuperset(expected):
        missing = sorted(expected - got)
        if len(missing) <= 8:
            warnings.append(f"sidecar_missing_row_indices:{missing}")
        else:
            warnings.append(f"sidecar_missing_row_indices_count:{len(missing)}")

    inst_f: str | None = None if args.instrument == "all" else args.instrument

    by_instrument: dict[str, Any] = {}
    for label, filt in (("all", None), ("kospi", "kospi"), ("btc", "btc")):
        by_lens: dict[str, Any] = {}
        for lk in ("logos", "myeongni", "sasang"):
            by_lens[lk] = _agree_counts(score_rows, per_by_idx, lk, filt)
        by_instrument[label] = by_lens

    by_lens_primary = by_instrument[args.instrument]

    by_dated_aux: dict[str, Any] = {}
    for aux_key in ("myeongni_16_state_jsonl", "sasang_dynamics_jsonl"):
        by_dated_aux[aux_key] = {}
        for label, filt in (("all", None), ("kospi", "kospi"), ("btc", "btc")):
            by_dated_aux[aux_key][label] = _agree_dated_aux_mapping_target(score_rows, per_by_idx, aux_key, filt)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": FORMAT_VERSION,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "instrument_filter": args.instrument,
        "paired_score_ref": _rel(args.score_json),
        "sidecar_ref": _rel(args.sidecar_json),
        "score_row_count": len(score_rows),
        "per_date_feature_count": len(per_date),
        "sidecar_row_index_map_size": len(per_by_idx),
        "by_lens": by_lens_primary,
        "by_instrument": by_instrument,
        "by_dated_aux": by_dated_aux,
        "warnings": warnings,
        "notes_ko": [
            "per_date 행은 paired_row_index(유효 시)로 점수 rows에 매핑; 없으면 나열 순서.",
            "렌즈 direction_score 부호→bull/bear/neutral; 적중은 문자열 일치만(승격 게이트 미사용).",
            "by_instrument는 kospi/btc/all 동시 집계; by_lens는 --instrument 선택에 해당.",
            "by_dated_aux: 사이드카 dated_source_snapshots_asof_eval_date.snapshot.mapping_target를 bull/bear/neutral로 해석해 점수 행과 비교(데이터 없으면 skipped 증가).",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
