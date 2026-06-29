#!/usr/bin/env python3
"""JSONL weather ground truth → general_prophecy triplet registry (3 lens rows per day)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GP_SCHEMA = ROOT / "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json"
RUBRIC = (
    "TRIPLET_SHARED_RUBRIC_v1. TRUE: KMA 공개 일별 관측 STN_ID=108, 관측일 {obs}(Asia/Seoul) "
    "일강수량 > 0.1mm. FALSE: ≤0.1mm 또는 0.0mm 보고. VOID: 공표 없음·단위 불명. "
    "재분석 시 최종 공표값. [HYPO] 명리·사상 인과 주장 금지; 측정 전용."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _station_slug(station_or_region_id: str) -> str:
    s = station_or_region_id.lower()
    digits = "".join(ch for ch in s if ch.isdigit())
    if "seoul" in s and digits:
        return f"seoul{digits}"
    slug = "".join(ch for ch in s if ch.isalnum())
    return slug[:32] or "unknown"


def _deadline_utc(obs_date: str) -> str:
    dt = datetime.strptime(obs_date, "%Y-%m-%d") + timedelta(days=1)
    return dt.strftime("%Y-%m-%dT15:00:00Z")


def _issued_utc(obs_date: str) -> str:
    dt = datetime.strptime(obs_date, "%Y-%m-%d") - timedelta(days=1)
    return dt.strftime("%Y-%m-%dT06:00:00Z")


def _resolved_utc(obs_date: str) -> str:
    dt = datetime.strptime(obs_date, "%Y-%m-%d") + timedelta(days=1)
    return dt.strftime("%Y-%m-%dT08:00:00Z")


def _question_id(station_slug: str, obs_date: str, lens: str) -> str:
    return f"btrack.weather_hist.{station_slug}.{obs_date.replace('-', '')}.{lens}"


def _load_gt_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_forecasts(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        doc = json.loads(line)
        qid = doc.get("question_id")
        if isinstance(qid, str):
            out[qid] = doc
    return out


def _lens_meta(lens: str) -> tuple[str, str, str]:
    if lens == "lens_myeongri":
        return ("명리(myeongri)", "lens_myeongri", "llm_ensemble")
    if lens == "lens_sasang":
        return ("사상(sasang)", "lens_sasang", "llm_ensemble")
    return ("융합 v1(사전 등록)", "lens_fusion_v1", "hybrid")


def _forecast_block(
    *,
    lens: str,
    qid: str,
    obs_date: str,
    sidecar: dict[str, Any] | None,
    stub_p: float,
) -> dict[str, Any]:
    p = stub_p
    source_detail = f"lens_{lens}_p{stub_p:.4f}; replace with model run id"
    source_kind = "llm_ensemble"
    if sidecar is not None:
        p = float(sidecar.get("probability_0_1", stub_p))
        source_detail = str(sidecar.get("source_detail") or source_detail)
        if lens == "lens_fusion_v1":
            source_kind = "hybrid"
            source_detail = sidecar.get("source_detail") or (
                f"pre_registered_fusion_v1_linear_0p5_0p5: P=0.5*P_m+0.5*P_s -> {p:.4f}; frozen before outcome"
            )
    return {
        "issued_at_utc": _issued_utc(obs_date),
        "probability_0_1": round(p, 4),
        "source_kind": source_kind,
        "source_detail": source_detail,
        "brier_ready": True,
    }


def _build_question(
    row: dict[str, Any],
    *,
    lens: str,
    forecasts_map: dict[str, dict[str, Any]],
    stub_p: float,
) -> dict[str, Any]:
    obs_date = str(row["observation_date_local"])
    station = str(row["station_or_region_id"])
    station_slug = _station_slug(station)
    lens_label, lens_tag, _ = _lens_meta(lens)
    qid = _question_id(station_slug, obs_date, lens)
    binary = bool(row.get("precip_binary_gt_0_1mm"))
    return {
        "schema": "general_prophecy_question_v1",
        "research_rail": "B",
        "boundary_ack": True,
        "question_id": qid,
        "prophecy_track": "general",
        "question_text": (
            f"[HYPO][walkforward_hist] 동일 관측·동일 해소. 렌즈={lens_label} P(강수) 슬롯. "
            f"서울 ASOS STN_ID=108, 관측일 {obs_date} Asia/Seoul 달력일 일강수량이 0.1mm를 초과하는가?"
        ),
        "domain_tags": [
            "weather",
            "walkforward_hist",
            "seoul",
            "btrack",
            "triplet_shared_target",
            "weather_calibration_v1",
            lens_tag,
        ],
        "resolution_deadline_utc": _deadline_utc(obs_date),
        "resolution_criteria": RUBRIC.format(obs=obs_date),
        "outcome_spec": {
            "kind": "binary",
            "true_label": "daily_precip_gt_0_1mm",
            "false_label": "daily_precip_le_0_1mm",
        },
        "forecasts": [
            _forecast_block(
                lens=lens,
                qid=qid,
                obs_date=obs_date,
                sidecar=forecasts_map.get(qid),
                stub_p=stub_p,
            )
        ],
        "resolution": {
            "status": "resolved",
            "resolved_at_utc": _resolved_utc(obs_date),
            "outcome_binary": binary,
            "resolver_notes": (
                f"Synthetic resolver from ground_truth_jsonl; precip_binary_gt_0_1mm={binary}."
            ),
            "evidence_uris": ["https://data.kma.go.kr/"],
        },
        "layer3_interpretation_ref": "internal:weather_lens_triplet_walkforward_v1",
        "epistemic_firewall": {
            "l1_probability_fields": ["forecasts[].probability_0_1"],
            "l3_narrative_forbidden_in": ["forecasts", "resolution"],
        },
    }


def build_registry(
    gt_jsonl: Path,
    *,
    out_path: Path,
    forecasts_jsonl: Path | None,
    stub_p: float,
) -> dict[str, Any]:
    rows = _load_gt_rows(gt_jsonl)
    forecasts_map: dict[str, dict[str, Any]] = {}
    if forecasts_jsonl is not None and forecasts_jsonl.is_file():
        forecasts_map = _load_forecasts(forecasts_jsonl)
    questions: list[dict[str, Any]] = []
    for row in rows:
        station_slug = _station_slug(str(row.get("station_or_region_id", "unknown")))
        obs_date = str(row.get("observation_date_local", ""))
        for lens in ("lens_myeongri", "lens_sasang", "lens_fusion_v1"):
            questions.append(
                _build_question(row, lens=lens, forecasts_map=forecasts_map, stub_p=stub_p)
            )
    registry: dict[str, Any] = {
        "schema": "general_prophecy_registry_v1",
        "version": "1.0.0",
        "research_rail": "B",
        "boundary_ack": True,
        "generated_at_utc": _utc_now(),
        "git_commit_hint": "build_weather_triplet_registry_v1",
        "questions": questions,
    }
    return registry


def _validate_registry(doc: dict[str, Any]) -> None:
    if not GP_SCHEMA.is_file():
        return
    from jsonschema import Draft202012Validator

    schema = json.loads(GP_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(doc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True, help="Ground-truth JSONL")
    ap.add_argument("--output", type=Path, required=True, help="Registry JSON out")
    ap.add_argument("--forecasts-jsonl", type=Path, default=None)
    ap.add_argument("--auto-forecasts-sidecar", action="store_true")
    ap.add_argument("--stub-probability", type=float, default=0.5)
    ap.add_argument("--skip-schema-validate", action="store_true")
    ns = ap.parse_args()
    if not ns.input.is_file():
        print(f"missing input: {ns.input}", file=sys.stderr)
        return 2

    forecasts_path = ns.forecasts_jsonl
    temp_sidecar: Path | None = None
    if ns.auto_forecasts_sidecar:
        temp_sidecar = Path(tempfile.mkstemp(suffix="_weather_forecasts_sidecar.jsonl")[1])
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "weather_gt_jsonl_to_forecasts_sidecar_v1.py"),
            "--input",
            str(ns.input),
            "--output",
            str(temp_sidecar),
        ]
        rc = subprocess.call(cmd, cwd=str(ROOT))
        if rc != 0:
            return rc
        forecasts_path = temp_sidecar

    try:
        registry = build_registry(
            ns.input,
            out_path=ns.output,
            forecasts_jsonl=forecasts_path,
            stub_p=ns.stub_probability,
        )
        if not ns.skip_schema_validate:
            try:
                _validate_registry(registry)
            except ImportError:
                print("warn: jsonschema missing; skipped registry validation", file=sys.stderr)
            except Exception as exc:
                print(f"registry validation failed: {exc}", file=sys.stderr)
                return 1
        ns.output.parent.mkdir(parents=True, exist_ok=True)
        ns.output.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {ns.output} questions={len(registry['questions'])} gt_rows={len(_load_gt_rows(ns.input))}")
        return 0
    finally:
        if temp_sidecar is not None and temp_sidecar.is_file():
            try:
                temp_sidecar.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
