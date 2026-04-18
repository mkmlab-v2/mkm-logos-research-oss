# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.76, L:0.85, K:0.54, M:0.66}
# Balance: 86
# Purpose: Phase-3 observation join — score rows + insight sidecar per_date rows (no gate inputs; SSOT score unchanged).
# Keywords: btrack, prophecy, sidecar, phase3, overlay
"""Emit a joined observation view: btrack_prophecy_score_v1 rows + sidecar per_date_features.

Promotion gates and walkforward must keep using ``btrack_prophecy_score_latest.json`` only.
This artifact is research-only alignment for notebooks and future overlay experiments.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_SIDECAR = ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_overlay_view_v1_latest.json"

SCHEMA = "btrack_prophecy_score_insight_overlay_view_v1"
FORMAT_VERSION = "1.0.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _pdf_by_paired_index(pdf: list[Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for item in pdf:
        if not isinstance(item, dict):
            continue
        idx = item.get("paired_row_index")
        if isinstance(idx, int) and idx >= 0:
            out[idx] = item
    return out


def _join_rows(
    score_rows: list[dict[str, Any]],
    pdf: list[Any] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    if not pdf:
        return [{"score_row": r, "insight_sidecar_observation": None} for r in score_rows], ["per_date_features_missing_or_empty"]
    by_i = _pdf_by_paired_index([x for x in pdf if isinstance(x, dict)])
    joined: list[dict[str, Any]] = []
    for i, row in enumerate(score_rows):
        obs = by_i.get(i)
        if obs is None and i < len(pdf) and isinstance(pdf[i], dict):
            obs = pdf[i]
        if obs and isinstance(row, dict):
            se = str(row.get("eval_date") or "")
            oe = str(obs.get("eval_date") or "")
            si = str(row.get("instrument") or "").lower()
            oi = str(obs.get("instrument") or "").lower()
            if se and oe and se != oe:
                warnings.append(f"row_index={i} eval_date mismatch score={se} sidecar={oe}")
            if si and oi and si != oi:
                warnings.append(f"row_index={i} instrument mismatch score={si} sidecar={oi}")
        joined.append({"score_row": row, "insight_sidecar_observation": obs})
    return joined, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--insight-sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score = _load(args.score_json)
    side = _load(args.insight_sidecar_json)
    if not score:
        raise SystemExit(f"score JSON missing or invalid: {args.score_json}")
    if not side:
        raise SystemExit(f"sidecar JSON missing or invalid: {args.insight_sidecar_json}")

    score_schema = str(score.get("schema") or "")
    rows_raw = score.get("rows")
    score_rows = [x for x in rows_raw if isinstance(x, dict)] if isinstance(rows_raw, list) else []

    pdf_raw = side.get("per_date_features")
    pdf = [x for x in pdf_raw if isinstance(x, dict)] if isinstance(pdf_raw, list) else None

    joined, warnings = _join_rows(score_rows, pdf)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": FORMAT_VERSION,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "description_ko": "점수 SSOT는 변경하지 않음. gates·walkforward는 score JSON만 입력.",
        "paired_score_ref": _rel(args.score_json),
        "paired_score_schema": score_schema or None,
        "insight_sidecar_ref": _rel(args.insight_sidecar_json),
        "insight_sidecar_schema": side.get("schema"),
        "insight_sidecar_format": side.get("version"),
        "paired_row_count": len(score_rows),
        "joined_row_count": len(joined),
        "alignment_warnings": warnings,
        "joined_rows": joined,
        "notes_ko": [
            "btrack_prophecy_score_v1의 rows[]는 score_row에 그대로 복사.",
            "insight_sidecar_observation은 동일 paired_row_index의 per_date_features 관측 블록.",
            "승격·게이트 입력으로 이 파일을 사용하지 말 것.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
