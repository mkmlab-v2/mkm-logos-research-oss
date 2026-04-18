# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.74, L:0.86, K:0.52, M:0.64}
# Balance: 85
# Purpose: Emit insight sidecar next to btrack_prophecy_score_v1 (no score row mutation; optional per-row lens snapshots).
# Keywords: btrack, prophecy, sidecar, phase3, insight, lens
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_BRIDGE = ROOT / "docs" / "final" / "artifacts" / "btrack_insight_promotion_bridge_index_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_insight_sidecar_v1_latest.json"

SCHEMA = "btrack_prophecy_score_insight_sidecar_v1"
SIDEcar_FORMAT = "1.1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _optional_ref(p: Path) -> dict[str, Any]:
    return {"path": _rel(p), "exists": p.is_file()}


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _lens_minimal(lens_id: str, data: dict[str, Any]) -> dict[str, Any]:
    scores = data.get("scores") if isinstance(data.get("scores"), dict) else {}
    out: dict[str, Any] = {
        "lens_id": str(data.get("lens_id") or lens_id),
        "direction_score": scores.get("direction_score"),
        "confidence": scores.get("confidence"),
        "lens_ts_utc": data.get("ts_utc"),
    }
    if lens_id == "sasang":
        stream = data.get("sasang_stream_outputs")
        if isinstance(stream, dict):
            mr = stream.get("machine_readables")
            if isinstance(mr, dict):
                out["machine_readables"] = mr
    if lens_id == "myeongni":
        stream = data.get("myeongri_stream_outputs")
        if isinstance(stream, dict):
            for k in ("state_id", "run_id", "experiment_id"):
                if k in stream:
                    out[k] = stream.get(k)
    if lens_id == "logos":
        stream = data.get("logos_stream_outputs")
        if isinstance(stream, dict):
            out["verses_with_simple_4d"] = stream.get("verses_with_simple_4d")
            out["batch_rows_total"] = stream.get("batch_rows_total")
    return out


def _build_lens_snapshot_block() -> tuple[dict[str, Any], dict[str, Any | None]]:
    paths = {
        "logos": ROOT / "docs/final/artifacts/logos_independent_lens_latest.json",
        "myeongni": ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json",
        "sasang": ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json",
    }
    refs = {k: _optional_ref(p) for k, p in paths.items()}
    minimal: dict[str, Any | None] = {}
    for lid, p in paths.items():
        raw = _load_json(p)
        minimal[lid] = _lens_minimal(lid, raw) if raw else None
    return refs, minimal


def _per_date_features(rows: list[dict[str, Any]], lens_snap: dict[str, Any | None]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "").strip()
        ins = str(row.get("instrument") or "").strip().lower()
        out.append(
            {
                "eval_date": ed,
                "instrument": ins,
                "observation_only": True,
                "paired_row_index": i,
                "lens_scores_snapshot": {
                    "logos": lens_snap.get("logos"),
                    "myeongni": lens_snap.get("myeongni"),
                    "sasang": lens_snap.get("sasang"),
                },
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--bridge-index", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--skip-per-date",
        action="store_true",
        help="Emit per_date_features=null (legacy stub shape).",
    )
    ap.add_argument(
        "--enable-experimental-attribution",
        action="store_true",
        help="Reserved; default build keeps experimental_attribution_enabled=false.",
    )
    args = ap.parse_args()

    score_schema: str | None = None
    rows: list[dict[str, Any]] = []
    score_raw = _load_json(args.score_json)
    if score_raw:
        score_schema = str(score_raw.get("schema") or "")
        r = score_raw.get("rows")
        if isinstance(r, list):
            rows = [x for x in r if isinstance(x, dict)]

    lens_refs, lens_minimal = _build_lens_snapshot_block()

    per_date: list[dict[str, Any]] | None
    if args.skip_per_date:
        per_date = None
    elif not rows:
        per_date = None
    else:
        per_date = _per_date_features(rows, lens_minimal)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": SIDEcar_FORMAT,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "paired_score_ref": _rel(args.score_json),
        "paired_score_schema": score_schema,
        "paired_row_count": len(rows),
        "bridge_index_ref": _rel(args.bridge_index) if args.bridge_index.is_file() else None,
        "experimental_attribution_enabled": bool(args.enable_experimental_attribution),
        "lens_snapshot_refs": lens_refs,
        "lens_globals_for_sidecar": lens_minimal,
        "feature_contract_v1": [
            "lens_majority_agreement_score_global",
            "notebooklm_guardrail_token_rate_prior_window",
            "myeongni_insight_log_lines_prior_window",
        ],
        "per_date_features": per_date,
        "notes_ko": [
            "score JSON의 rows·predicted_direction는 변경하지 않음.",
            "per_date_features의 렌즈 값은 현재 글로벌 스냅샷을 행마다 복제(B-track 관측; 날짜 조건부 아님).",
            "승격·walkforward 게이트는 기존 btrack_prophecy_score_v1만 입력.",
            "실험 병합은 별 계약·회귀 후 experimental_attribution_enabled 검토.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
