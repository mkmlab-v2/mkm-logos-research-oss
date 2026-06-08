"""build_showroom_macro_horizon_2030_slice_v1.py CLI and slice contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_showroom_macro_horizon_2030_slice_v1.py"
SOURCE = ROOT / "docs/final/artifacts/logos_macro_horizon_2030_scenario_v1_latest.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_missing_source_exits_2(tmp_path: Path) -> None:
    r = _run(
        "--workspace-root",
        str(tmp_path),
        "--source",
        "missing/scenario.json",
        "--out",
        "out/slice.json",
    )
    assert r.returncode == 2


@pytest.mark.skipif(not SOURCE.is_file(), reason="2030 scenario artifact missing")
def test_repo_source_emit_validates() -> None:
    try:
        import jsonschema  # noqa: WPS433
    except ImportError:
        pytest.skip("jsonschema not installed")

    out_rel = "reports/showroom_macro_horizon_2030_slice_pytest_tmp.json"
    out_path = ROOT / out_rel.replace("/", os.sep)
    try:
        r = _run("--workspace-root", str(ROOT), "--out", out_rel)
        assert r.returncode == 0, r.stderr + r.stdout
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "showroom_macro_horizon_2030_slice_v1"
        assert data["no_trade_signals"] is True
        assert len(data["macro_badges"]) >= 3
        assert data["btc_path"]["not_calibrated"] is True
        assert data["hypo_banner"].startswith("[HYPO]")
        schema = json.loads(
            (ROOT / "docs/final/schemas/showroom_macro_horizon_2030_slice_v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.validate(instance=data, schema=schema)
    finally:
        if out_path.is_file():
            out_path.unlink()


@pytest.mark.skipif(not SOURCE.is_file(), reason="2030 scenario artifact missing")
def test_badges_include_rates_inflation_liquidity_kinds() -> None:
    from scripts.build_showroom_macro_horizon_2030_slice_v1 import build_slice

    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    slice_doc = build_slice(doc)
    kinds = {b["value_kind"] for b in slice_doc["macro_badges"]}
    ids = {b["badge_id"] for b in slice_doc["macro_badges"]}
    assert "registry_p" in kinds
    assert "risk_signal" in kinds
    assert "rates_path" in ids
    assert "inflation_patch" in ids
    assert "liquidity_stress" in ids


@pytest.mark.skipif(not SOURCE.is_file(), reason="2030 scenario artifact missing")
def test_slice_includes_lens_media_bind() -> None:
    from scripts.build_showroom_macro_horizon_2030_slice_v1 import build_slice

    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    slice_doc = build_slice(doc)
    bind = slice_doc.get("lens_media_bind") or {}
    assert bind.get("hypothesis_class") == "HYPO"
    assert bind.get("non_gating") is True
    assert bind.get("showroom_display_mode") in ("idle", "defend", "attack")
    assert bind.get("playback_id", "").startswith("LM_HP050_")
    assert "playback_id=" in bind.get("media_hub_query", "")
    assert bind.get("sasang_primary") in ("soyang", "taeyang", "taeeum", "soeum")
    assert bind.get("sasang_source")
