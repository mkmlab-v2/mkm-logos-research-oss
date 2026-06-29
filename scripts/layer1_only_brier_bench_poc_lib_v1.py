"""Shared helpers for Layer-1-only Brier bench PoC (B-track wall)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DEFAULT_COHORT = ROOT / "docs" / "final" / "artifacts" / "layer1_only_brier_bench_poc_v1_latest.json"
DEFAULT_MAP = ROOT / "docs" / "final" / "artifacts" / "layer1_only_brier_bench_poc_registry_map_v1.json"
DEFAULT_REGISTRY = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
SCHEMA_PATH = ROOT / "docs" / "final" / "GENERAL_PROPHECY_SCHEMA_V1.json"

FORBIDDEN_MODEL_SOURCES = frozenset(
    {"logos", "myeongri", "sasang", "layer3", "lens_narrative", "biblical_narrative"}
)


def load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    if ENV_PATH.is_file():
        load_dotenv(ENV_PATH, override=False)


def fred_api_key_configured() -> bool:
    load_dotenv_if_present()
    return bool(os.environ.get("FRED_API_KEY", "").strip())


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_track_wall(poc_meta: dict[str, Any]) -> None:
    if poc_meta.get("track") != "B":
        raise ValueError("track must be B")
    if poc_meta.get("track_wall") != "B":
        raise ValueError("track_wall must be B")
    if poc_meta.get("auto_bridge_to_a") is not False:
        raise ValueError("auto_bridge_to_a must be false")


def assert_mechanical_forecast(row: dict[str, Any]) -> None:
    kind = str(row.get("model_source_kind") or "").strip().lower()
    if not kind.startswith("mechanical"):
        raise ValueError(f"{row.get('question_id')}: model_source_kind must be mechanical_*")
    detail = str(row.get("model_source_detail") or "").lower()
    for forbidden in FORBIDDEN_MODEL_SOURCES:
        if forbidden in kind or forbidden in detail:
            raise ValueError(f"{row.get('question_id')}: forbidden Layer-3 source in model fields")


def load_cohort(path: Path = DEFAULT_COHORT) -> dict[str, Any]:
    doc = load_json(path)
    if doc.get("schema") != "layer1_only_brier_bench_poc_v1":
        raise ValueError("cohort schema must be layer1_only_brier_bench_poc_v1")
    assert_track_wall(doc.get("poc_meta") or {})
    forecasts = [f for f in (doc.get("forecasts") or []) if isinstance(f, dict)]
    if len(forecasts) != 5:
        raise ValueError("PoC cohort must contain exactly 5 goldilocks forecasts")
    for row in forecasts:
        assert_mechanical_forecast(row)
    return doc


def load_registry_map(path: Path = DEFAULT_MAP) -> dict[str, dict[str, Any]]:
    doc = load_json(path)
    if doc.get("schema") != "layer1_only_brier_bench_poc_registry_map_v1":
        raise ValueError("map schema must be layer1_only_brier_bench_poc_registry_map_v1")
    if doc.get("auto_bridge_to_a") is not False:
        raise ValueError("registry map auto_bridge_to_a must be false")
    out: dict[str, dict[str, Any]] = {}
    for m in doc.get("mappings") or []:
        if not isinstance(m, dict):
            continue
        poc_id = m.get("poc_question_id")
        reg_id = m.get("registry_question_id")
        if isinstance(poc_id, str) and isinstance(reg_id, str):
            out[poc_id] = m
    return out


def parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def deadline_reached(deadline_utc: str, *, now: datetime | None = None) -> bool:
    dt = parse_utc(deadline_utc)
    if dt is None:
        return False
    ref = now or datetime.now(timezone.utc)
    return ref >= dt


def poc_row_to_registry_question(row: dict[str, Any], *, registry_question_id: str) -> dict[str, Any]:
    qtext = row.get("question_text")
    if not isinstance(qtext, str) or len(qtext) < 20:
        raise ValueError(f"{registry_question_id}: question_text too short")
    tags = row.get("domain_tags") if isinstance(row.get("domain_tags"), list) else []
    issued = utc_now()
    model_p = float(row["probability_model_p"])
    return {
        "schema": "general_prophecy_question_v1",
        "research_rail": "B",
        "boundary_ack": True,
        "question_id": registry_question_id,
        "question_text": qtext,
        "domain_tags": [t for t in tags if isinstance(t, str)],
        "prophecy_track": "general",
        "resolution_deadline_utc": row["resolution_deadline_utc"],
        "resolution_criteria": row["resolution_criteria"],
        "outcome_spec": {
            "kind": "binary",
            "true_label": "condition_met",
            "false_label": "condition_not_met",
        },
        "forecasts": [
            {
                "issued_at_utc": issued,
                "probability_0_1": model_p,
                "source_kind": "other",
                "source_detail": f"mechanical_reference_class_v1:{row.get('model_source_detail', 'poc')}",
                "brier_ready": True,
            },
            {
                "issued_at_utc": issued,
                "probability_0_1": float(row.get("probability_baseline_p", 0.5)),
                "source_kind": "baseline",
                "source_detail": "uniform_0_5_layer1_poc",
                "brier_ready": True,
            },
        ],
        "resolution": {"status": "pending"},
        "layer3_interpretation_ref": row.get(
            "layer3_interpretation_ref",
            "docs/final/artifacts/lens_predictive_validity_literature_review_v1_latest.md",
        ),
        "epistemic_firewall": {
            "l1_probability_fields": ["forecasts[].probability_0_1"],
            "l3_narrative_forbidden_in": ["forecasts", "resolution"],
        },
    }


def mechanical_forecast_snapshots(row: dict[str, Any]) -> list[dict[str, Any]]:
    issued = utc_now()
    model_p = float(row["probability_model_p"])
    baseline_p = float(row.get("probability_baseline_p", 0.5))
    detail = str(row.get("model_source_detail") or "poc")
    return [
        {
            "issued_at_utc": issued,
            "probability_0_1": model_p,
            "source_kind": "other",
            "source_detail": f"mechanical_reference_class_v1:{detail}",
            "brier_ready": True,
        },
        {
            "issued_at_utc": issued,
            "probability_0_1": baseline_p,
            "source_kind": "baseline",
            "source_detail": "uniform_0_5_layer1_poc",
            "brier_ready": True,
        },
    ]


def validate_registry(doc: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(doc)


def index_registry_questions(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for q in doc.get("questions") or []:
        if isinstance(q, dict) and isinstance(q.get("question_id"), str):
            out[q["question_id"]] = q
    return out
