# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.74, L:0.86, K:0.52, M:0.64}
# Balance: 85
# Purpose: Emit insight sidecar next to btrack_prophecy_score_v1 (no score row mutation; optional per-row lens snapshots).
# Keywords: btrack, prophecy, sidecar, phase3, insight, lens
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_BRIDGE = ROOT / "docs" / "final" / "artifacts" / "btrack_insight_promotion_bridge_index_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_insight_sidecar_v1_latest.json"

SCHEMA = "btrack_prophecy_score_insight_sidecar_v1"
SIDEcar_FORMAT = "1.3.0"

DEFAULT_NOTEBOOKLM_KPI = ROOT / "docs/final/artifacts/btrack_notebooklm_jsonl_kpi_latest.json"
DEFAULT_MYEONGNI_INSIGHT_LOG = ROOT / "data/myeongni/insight_observation_log.jsonl"


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


def _jsonl_line_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    n = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for _ in f:
                n += 1
    except OSError:
        return None
    return n


def _notebooklm_kpi_summary(kpi: dict[str, Any]) -> dict[str, Any]:
    dist = kpi.get("distributions") if isinstance(kpi.get("distributions"), dict) else {}
    ach = dist.get("answer_char_len") if isinstance(dist.get("answer_char_len"), dict) else {}
    out: dict[str, Any] = {
        "schema": kpi.get("schema"),
        "generated_at_utc": kpi.get("generated_at_utc"),
        "input_path": kpi.get("input_path"),
        "disclaimer": kpi.get("disclaimer"),
        "rows_total_valid": kpi.get("rows_total_valid"),
        "rows_skipped": kpi.get("rows_skipped"),
        "guardrail_keyword_rates": kpi.get("guardrail_keyword_rates"),
        "answer_char_len_mean": ach.get("mean"),
        "answer_char_len_median": ach.get("median"),
    }
    return out


def _insight_log_lines_per_calendar_day(path: Path) -> dict[str, int]:
    per_day: dict[str, int] = defaultdict(int)
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(o, dict):
                    continue
                ts = str(o.get("ts_utc") or "").strip()
                if len(ts) >= 10 and ts[4] == "-" and ts[7] == "-":
                    day = ts[:10]
                    per_day[day] += 1
    except OSError:
        return {}
    return dict(per_day)


def _cumulative_insight_lines_through(per_day: dict[str, int], eval_date: str) -> int:
    if not eval_date or len(eval_date) < 10:
        return 0
    return sum(c for d, c in per_day.items() if d <= eval_date[:10])


def _score_row_context(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "predicted_direction": row.get("predicted_direction"),
        "actual_direction": row.get("actual_direction"),
        "daily_return": row.get("daily_return"),
        "prev_close": row.get("prev_close"),
        "close": row.get("close"),
        "neutral_bps": row.get("neutral_bps"),
        "flow_score_for_reversal": row.get("flow_score_for_reversal"),
    }


def _myeongni_insight_log_meta(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        st = path.stat()
    except OSError:
        return None
    lines = _jsonl_line_count(path)
    return {
        "path": _rel(path),
        "bytes": int(st.st_size),
        "jsonl_line_count": lines,
    }


def _per_date_features(
    rows: list[dict[str, Any]],
    lens_snap: dict[str, Any | None],
    insight_per_day: dict[str, int] | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "").strip()
        ins = str(row.get("instrument") or "").strip().lower()
        item: dict[str, Any] = {
            "eval_date": ed,
            "instrument": ins,
            "observation_only": True,
            "paired_row_index": i,
            "score_row_context": _score_row_context(row),
            "lens_scores_snapshot": {
                "logos": lens_snap.get("logos"),
                "myeongni": lens_snap.get("myeongni"),
                "sasang": lens_snap.get("sasang"),
            },
            "lens_snapshot_attribution": "global_mirrored_v1",
        }
        if insight_per_day is not None:
            item["myeongni_insight_lines_cumulative_through_eval_date"] = _cumulative_insight_lines_through(
                insight_per_day, ed
            )
        out.append(item)
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
    ap.add_argument(
        "--skip-external-observations",
        action="store_true",
        help="Omit NotebookLM KPI summary and Myeongni insight log meta.",
    )
    ap.add_argument("--notebooklm-kpi-json", type=Path, default=DEFAULT_NOTEBOOKLM_KPI)
    ap.add_argument("--myeongni-insight-log", type=Path, default=DEFAULT_MYEONGNI_INSIGHT_LOG)
    ap.add_argument(
        "--skip-insight-log-cumulative",
        action="store_true",
        help="Do not attach per-row cumulative counts from insight_observation_log.jsonl.",
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

    insight_per_day: dict[str, int] | None = None
    if not args.skip_insight_log_cumulative:
        insight_per_day = _insight_log_lines_per_calendar_day(args.myeongni_insight_log)

    per_date: list[dict[str, Any]] | None
    if args.skip_per_date:
        per_date = None
    elif not rows:
        per_date = None
    else:
        per_date = _per_date_features(rows, lens_minimal, insight_per_day)

    nb_summary: dict[str, Any] | None = None
    nb_ref: str | None = None
    mn_meta: dict[str, Any] | None = None
    if not args.skip_external_observations:
        kpi_raw = _load_json(args.notebooklm_kpi_json)
        if kpi_raw:
            nb_summary = _notebooklm_kpi_summary(kpi_raw)
            nb_ref = _rel(args.notebooklm_kpi_json)
        mn_meta = _myeongni_insight_log_meta(args.myeongni_insight_log)

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
        "lens_attribution_mode": "global_mirrored_with_row_score_context_v1",
        "phase3_merge": {
            "status": "not_started",
            "target": "btrack_prophecy_score_v1_optional_overlay_or_walkforward_branch",
            "note_ko": "점수 본문 병합·게이트 연동은 별 스키마·플래그·회귀 PR에서만 진행.",
        },
        "lens_snapshot_refs": lens_refs,
        "lens_globals_for_sidecar": lens_minimal,
        "notebooklm_observation_kpi_ref": nb_ref,
        "notebooklm_observation_kpi_summary": nb_summary,
        "myeongni_insight_observation_log_meta": mn_meta,
        "feature_contract_v1": [
            "lens_majority_agreement_score_global",
            "notebooklm_guardrail_token_rate_prior_window",
            "myeongni_insight_log_lines_prior_window",
        ],
        "per_date_features": per_date,
        "notes_ko": [
            "score JSON의 rows·predicted_direction는 변경하지 않음.",
            "lens_scores_snapshot은 글로벌 렌즈 스냅샷 복제(lens_snapshot_attribution); score_row_context는 해당 행의 점수 SSOT 필드 복사(평가일·종목 정렬).",
            "myeongni_insight_lines_cumulative_through_eval_date는 insight 로그 ts_utc 달력일이 eval_date 이하인 줄 수 누적(관측).",
            "승격·walkforward 게이트는 기존 btrack_prophecy_score_v1만 입력.",
            "실험 병합은 별 계약·회귀 후 experimental_attribution_enabled 검토.",
            "notebooklm_observation_kpi_summary·명리 로그 파일 메타는 전역 관측.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
