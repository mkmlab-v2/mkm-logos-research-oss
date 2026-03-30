# @MKM12-METADATA
# Type: Logic
# Purpose: Validate ENTRY_16 source-hunt JSONL contract.
# Keywords: entry16, dss, source-hunt, jsonl

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_LOG = _ROOT / "docs" / "final" / "artifacts" / "entry16_source_hunt_log.jsonl"

_REQUIRED = (
    "source_url",
    "source_title",
    "publisher_or_host",
    "resource_type",
    "manuscript_id",
    "djd_volume",
    "page_range",
    "fragment_sigla",
    "line_anchor",
    "extant_verses_claim",
    "ezra_2_54_direct_witness",
    "evidence_quote",
    "confidence",
    "access_mode",
    "last_checked_utc",
)


def _rows(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            yield json.loads(s)


def test_entry16_source_hunt_log_contract() -> None:
    assert _LOG.is_file(), f"missing log: {_LOG}"
    rows = list(_rows(_LOG))
    assert rows, "entry16 source hunt log must not be empty"
    for i, row in enumerate(rows):
        for key in _REQUIRED:
            assert key in row, f"row[{i}] missing key: {key}"
            assert str(row[key]).strip(), f"row[{i}] empty value: {key}"
        assert row["manuscript_id"] == "4Q117", f"row[{i}] manuscript_id must be 4Q117"
        assert row["ezra_2_54_direct_witness"] in {"yes", "no", "unknown"}, (
            f"row[{i}] invalid ezra_2_54_direct_witness"
        )
        assert row["confidence"] in {"high", "med", "low"}, f"row[{i}] invalid confidence"
        assert row["access_mode"] in {"public", "login", "institutional", "paywalled"}, (
            f"row[{i}] invalid access_mode"
        )
        datetime.fromisoformat(str(row["last_checked_utc"]).replace("Z", "+00:00"))


def test_entry16_source_hunt_no_duplicate_source_url() -> None:
    rows = list(_rows(_LOG))
    urls = [str(r["source_url"]).strip() for r in rows]
    assert len(urls) == len(set(urls)), "source_url must be unique per row"


def test_entry16_source_hunt_has_at_least_one_negative_or_unknown_witness() -> None:
    rows = list(_rows(_LOG))
    values = {str(r["ezra_2_54_direct_witness"]).strip() for r in rows}
    assert values & {"no", "unknown"}, "log must include unresolved/negative witness evidence"


def test_entry16_yes_witness_rows_require_concrete_anchor() -> None:
    rows = list(_rows(_LOG))
    yes_rows = [r for r in rows if str(r.get("ezra_2_54_direct_witness", "")).strip() == "yes"]
    for i, row in enumerate(yes_rows):
        line_anchor = str(row.get("line_anchor", "")).strip().lower()
        assert line_anchor not in {
            "",
            "unknown",
            "none",
            "none (catalog-level)",
            "none (image metadata only)",
            "none (contents-level only)",
        }, f"yes-row[{i}] must include concrete line anchor"
        assert "tbd" not in line_anchor, f"yes-row[{i}] line_anchor must not be TBD"
        combined_text = f'{row.get("extant_verses_claim", "")} {row.get("evidence_quote", "")}'.lower()
        assert ("2:54" in combined_text) or ("2,54" in combined_text), (
            f"yes-row[{i}] must explicitly mention Ezra 2:54"
        )
        assert len(str(row.get("evidence_quote", "")).strip()) >= 20, (
            f"yes-row[{i}] evidence_quote too short for reproducibility"
        )
