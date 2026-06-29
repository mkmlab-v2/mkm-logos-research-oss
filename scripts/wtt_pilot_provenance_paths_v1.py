"""Shared paths for WTT pilot provenance ledger v1."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE_DIR = ROOT / "data/wtt/provenance"
SCHEMA_PATH = ROOT / "docs/final/schemas/wtt_pilot_provenance_v1.schema.json"
DEFAULT_REPORT = ROOT / "reports/wtt_pilot_provenance_check_v1_latest.json"


def provenance_path_for_tenant(tenant_id: str) -> Path:
    return PROVENANCE_DIR / f"{tenant_id}.provenance.json"


def intake_path_for_tenant(tenant_id: str) -> Path:
    return ROOT / "data/wtt/intake" / f"{tenant_id}.jsonl"
