"""
Manseryeok provenance + boundary heuristics for B-track artifacts.

These helpers do NOT compute observatory-grade 節入 times. They tag outputs so
downstream agents (NotebookLM, evaluators) never misread stub/approx pipelines
as precision engines.

Anchor days match the legacy static approximation pattern (month -> nominal day)
documented for the old v3 stub — used only for *risk tagging*, not astronomy.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# B-track pilot bench JSONL: slim row points here for full scope dict.
BENCH_SCOPE_REF_DIRECT_V1 = "btrack_pilot_bench_direct_v1"
BENCH_SCOPE_REF_OBSERVED_V1 = "btrack_pilot_bench_observed_v1"
BENCH_SCOPE_REF_CROSS_REF_BOOTSTRAP_V1 = "btrack_pilot_bench_cross_ref_bootstrap_v1"
BENCH_SCOPE_MANIFEST_RELPATH = Path("data") / "logos" / "btrack_pilot" / "bench" / "BENCH_MANSERYEOK_SCOPE_MANIFEST_V1.json"
MANSE_PRECISION_RUNTIME_POINTER_RELPATH = Path("docs") / "final" / "MANSE_PRECISION_RUNTIME_POINTER_V1.json"
_WORKSPACE_ROOT_FALLBACK = Path(__file__).resolve().parents[2]

# Nominal solar-term anchor (day-of-month) per calendar month — legacy stub parity.
_JEOLGI_ANCHOR_DOM: dict[int, int] = {
    1: 5,
    2: 4,
    3: 5,
    4: 5,
    5: 5,
    6: 6,
    7: 7,
    8: 7,
    9: 7,
    10: 8,
    11: 7,
    12: 7,
}


def jeolgi_boundary_risk_day(solar_month: int, solar_day: int, window_days: int = 1) -> bool:
    """True if solar day is within ``window_days`` of the stub anchor for that month."""
    if not 1 <= solar_month <= 12 or not 1 <= solar_day <= 31:
        return False
    anchor = _JEOLGI_ANCHOR_DOM.get(solar_month)
    if anchor is None:
        return False
    return abs(solar_day - anchor) <= window_days


def tag_excluded_from_jaccard_heuristic(
    solar_month: int,
    solar_day: int,
    *,
    window_days: int = 1,
    engine_is_approx: bool = True,
) -> bool:
    """If using an approx engine, suggest dropping this row from Jaccard-style lens metrics."""
    if not engine_is_approx:
        return False
    return jeolgi_boundary_risk_day(solar_month, solar_day, window_days=window_days)


def approx_stub_pipeline_metadata() -> dict[str, Any]:
    """Default provenance block for static month/day stub pipelines."""
    return {
        "manseryeok_model": "static_month_day_approx_v3",
        "jeolgi_uncertainty": "boundary_days_high_risk",
        "manseryeok_provenance_note": (
            "Static month/day jeolgi anchors only — not observatory ephemeris. "
            "Month/hour pillars near solar-term boundaries may disagree with "
            "professional almanacs; do not use for legal, medical, or trading triggers."
        ),
    }


def multilens_p1_compression_scope() -> dict[str, Any]:
    """Fence for P1 multilens A/B artifacts: Jaccard here is compression fidelity, not gapja."""
    return {
        "manseryeok_applicable": False,
        "jaccard_metric_domain": "compression_token_reconstruction",
        "manseryeok_scope_note": (
            "multilens_p1_ab_* reports: avg_reconstruction_fidelity_jaccard measures "
            "compressed vs baseline token overlap — not pillar or manse agreement. "
            "Do not merge approx_stub_pipeline_metadata() into these scores as if manse-derived."
        ),
    }


def logos_myeongni_state_join_scope() -> dict[str, Any]:
    """LOGOS_STATE_MAPPING_V1: cosine join of verse 4D to probe state vectors — not birth pillars."""
    return {
        "manseryeok_applicable": False,
        "artifact_domain": "verse_4d_to_myeongni_state_vector_cosine_assignment",
        "manseryeok_scope_note": (
            "Assignments maximize cosine between ranked verse 4D and 16_STATE_MASTER_PROBE vectors. "
            "No individual 출생 명식·절입·시주 is embedded; do not read as 만세력 정밀 결과."
        ),
    }


def btrack_myeongni_16_state_stream_scope() -> dict[str, Any]:
    """16-state experiment JSONL-derived reports: state_id transitions, not pillar tables."""
    return {
        "manseryeok_pillar_calc_applicable": False,
        "artifact_domain": "myeongni_16_state_experiment_stream",
        "manseryeok_scope_note": (
            "Derived from B-track experiment JSONL state_id sequences. "
            "If 간지·출생일시 is joined later, attach myeongni_row_provenance per row."
        ),
    }


def btrack_pilot_bench_scope(*, build_script: str, source_note: str = "") -> dict[str, Any]:
    """Per-row scope for data/logos/btrack_pilot/bench/*.jsonl builders (A/B SNR rows)."""
    note = (
        "Pilot bench rows carry confidence/SNR for state or CROSS_REF alignment — "
        "not 만세력 간지·절입 산출. "
    )
    if source_note.strip():
        note += source_note.strip()
    return {
        "manseryeok_pillar_calc_applicable": False,
        "artifact_domain": "btrack_pilot_bench_jsonl",
        "build_script": build_script,
        "manseryeok_scope_note": note,
    }


def myeongni_row_provenance(
    solar_month: int,
    solar_day: int,
    *,
    engine_is_approx: bool = True,
    jeolgi_window_days: int = 1,
) -> dict[str, Any]:
    """Single-row provenance for B-track JSON/JSONL (gapja or birth-derived pipelines)."""
    meta = (
        approx_stub_pipeline_metadata()
        if engine_is_approx
        else {
            "manseryeok_model": "precision_engine_unspecified",
            "jeolgi_uncertainty": "ephemeris_definition_ssot_required",
            "manseryeok_provenance_note": (
                "Precision: agents use Path B MCP stdio (mcp_athena_calculate_saju / verify_saju_date); "
                "SSOT docs/final/MANSE_PRECISION_RUNTIME_POINTER_V1.json. "
                "Batch/CI: same engine via colocated mkm-life or remote_lunisolar — not per-row MCP."
            ),
        }
    )
    excluded = tag_excluded_from_jaccard_heuristic(
        solar_month,
        solar_day,
        window_days=jeolgi_window_days,
        engine_is_approx=engine_is_approx,
    )
    return {
        **meta,
        "excluded_from_jaccard": excluded,
        "solar_month": solar_month,
        "solar_day": solar_day,
    }


def enrich_record_optional_solar_provenance(
    record: dict[str, Any],
    *,
    solar_month: int | None = None,
    solar_day: int | None = None,
    engine_is_approx: bool = True,
    jeolgi_window_days: int = 1,
) -> dict[str, Any]:
    """Return copy of record with ``manseryeok_provenance`` if both month and day are set."""
    out = dict(record)
    if solar_month is not None and solar_day is not None:
        out["manseryeok_provenance"] = myeongni_row_provenance(
            solar_month,
            solar_day,
            engine_is_approx=engine_is_approx,
            jeolgi_window_days=jeolgi_window_days,
        )
    return out


def upsert_bench_manseryeok_scope_manifest(
    workspace_root: Path,
    ref_id: str,
    scope: dict[str, Any],
) -> Path:
    """Merge one scope into the tracked bench manifest (multi-builder SSOT)."""
    path = workspace_root / BENCH_SCOPE_MANIFEST_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
    else:
        doc = {"schema": "btrack_bench_manseryeok_scope_manifest_v1", "scopes": {}}
    if doc.get("schema") != "btrack_bench_manseryeok_scope_manifest_v1":
        doc = {"schema": "btrack_bench_manseryeok_scope_manifest_v1", "scopes": {}}
    scopes = doc.setdefault("scopes", {})
    if not isinstance(scopes, dict):
        scopes = {}
        doc["scopes"] = scopes
    scopes[ref_id] = scope
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def resolve_bench_row_manseryeok_scope(
    row: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Resolve inline ``manseryeok_scope`` or ``manseryeok_scope_ref`` + manifest."""
    inline = row.get("manseryeok_scope")
    if isinstance(inline, dict):
        return inline
    ref = row.get("manseryeok_scope_ref")
    if not ref or not isinstance(ref, str) or manifest is None:
        return None
    scopes = manifest.get("scopes")
    if not isinstance(scopes, dict):
        return None
    out = scopes.get(ref)
    return out if isinstance(out, dict) else None


def load_bench_manseryeok_scope_manifest(workspace_root: Path) -> dict[str, Any] | None:
    path = workspace_root / BENCH_SCOPE_MANIFEST_RELPATH
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_manse_precision_runtime_pointer(workspace_root: Path | None = None) -> dict[str, Any] | None:
    """Load Layer-2 precision SSOT JSON (Path B MCP wiring, mkm-life batch hints)."""
    root = workspace_root if workspace_root is not None else _WORKSPACE_ROOT_FALLBACK
    path = root / MANSE_PRECISION_RUNTIME_POINTER_RELPATH
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def precision_mcp_runtime_metadata() -> dict[str, Any]:
    """Artifact tag when using Cursor MCP ``calculate_saju`` / verify tools (Layer-2, Path B stdio)."""
    return {
        "manseryeok_model": "mcp_athena_calculate_saju",
        "jeolgi_uncertainty": "engine_definition_ssot_required",
        "manseryeok_provenance_note": (
            "Official agent precision path: Path B MCP stdio (athena-manseryeok). "
            "SSOT: docs/final/MANSE_PRECISION_RUNTIME_POINTER_V1.json. "
            "Batch/CI should use the same engine without per-row MCP subprocesses."
        ),
    }
