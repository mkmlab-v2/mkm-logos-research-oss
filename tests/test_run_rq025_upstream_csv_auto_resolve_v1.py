from __future__ import annotations

import json
from pathlib import Path

from scripts.run_rq025_upstream_csv_auto_resolve_and_three_arm_v1 import (
    _load_sidecar_meta,
    _policy_from_csv,
    _sidecar_meta_candidates,
)

ROOT = Path(__file__).resolve().parents[1]


def test_sidecar_meta_candidates_order() -> None:
    p = Path("D:/data/real_upstream.csv")
    a, b = _sidecar_meta_candidates(p)
    assert a.name == "real_upstream.csv.meta.json"
    assert b.name == "real_upstream.meta.json"


def test_policy_from_csv_sidecar(tmp_path: Path) -> None:
    csv_path = tmp_path / "real_upstream.csv"
    csv_path.write_text("date\n2026-01-01\n", encoding="utf-8")
    meta_path = csv_path.with_name(csv_path.name + ".meta.json")
    meta_path.write_text(
        json.dumps(
            {
                "source_kind": "off_repo_upstream_sgp_lambda_batch",
                "upstream_production_batch": True,
                "boundary_ack": "certified batch",
            }
        ),
        encoding="utf-8",
    )
    meta, found = _load_sidecar_meta(csv_path)
    assert found == meta_path
    assert meta["upstream_production_batch"] is True
    kind, is_prod, ack, detail = _policy_from_csv(csv_path, default_kind="explicit_override")
    assert kind == "off_repo_upstream_sgp_lambda_batch"
    assert is_prod is True
    assert ack == "certified batch"
    assert "sidecar_meta" in detail


def test_policy_defaults_without_sidecar(tmp_path: Path) -> None:
    csv_path = tmp_path / "only.csv"
    csv_path.write_text("x\n1\n", encoding="utf-8")
    kind, is_prod, ack, detail = _policy_from_csv(csv_path, default_kind="explicit_override")
    assert kind == "explicit_override"
    assert is_prod is False
    assert ack is None
    assert detail == {}
