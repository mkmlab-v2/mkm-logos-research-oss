# @MKM12-METADATA
# Type: Logic
# Purpose: B-Track hypothesis generator smoke test (stub path).
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import tempfile

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "generate_btrack_hypothesis_prophecy_v1.py"
_BUNDLE = _ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"


def test_generate_script_exists() -> None:
    assert _SCRIPT.is_file()


def test_stub_outputs_valid_schema(tmp_path: Path) -> None:
    if not _BUNDLE.is_file():
        import pytest

        pytest.skip("bundle not built; run build_btrack_llm_input_bundle.py first")
    out = tmp_path / "hyp.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--bundle",
            str(_BUNDLE),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_hypothesis_prophecy_v1"
    assert doc.get("hypothesis_tier") == "B"
    assert "[HYPO]" in str(doc.get("label", ""))
    assert doc.get("prediction", {}).get("direction") in ("bull", "bear", "neutral", "abstain")
    assert doc.get("prediction", {}).get("instrument") == "btc"
    la = doc.get("lens_artifacts") or {}
    assert "shadow_minority_monthly" in la
    assert "independent_lens_shadow_minority_monthly" in str(la.get("shadow_minority_monthly", ""))
    runtime_meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
    assert runtime_meta.get("compression_bridge_available") is True
    bridge = runtime_meta.get("compression_bridge") if isinstance(runtime_meta.get("compression_bridge"), dict) else {}
    assert bridge.get("available") is True
    guard = runtime_meta.get("btc_only_guard") if isinstance(runtime_meta.get("btc_only_guard"), dict) else {}
    assert guard.get("enabled") is True


def test_btc_only_guard_blocks_non_btc_scope(tmp_path: Path) -> None:
    bad_bundle = tmp_path / "bad_bundle.json"
    bad_bundle.write_text(
        json.dumps(
            {
                "schema": "btrack_llm_input_bundle_v1",
                "artifacts": {
                    "macro_independent_lens": {
                        "scores": {"direction_score": 0.5, "confidence": 0.8},
                        "policy_scope": {"trading_primary_asset": "KOSPI200", "kospi_role": "gating"},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "hyp_bad.json"
    cp = subprocess.run(
        [sys.executable, str(_SCRIPT), "--bundle", str(bad_bundle), "--output", str(out)],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("prediction", {}).get("instrument") == "btc"
    assert doc.get("prediction", {}).get("direction") == "abstain"
    meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
    guard = meta.get("btc_only_guard") if isinstance(meta.get("btc_only_guard"), dict) else {}
    assert guard.get("blocked") is True


def test_validate_only_accepts_good_doc(tmp_path: Path) -> None:
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps(
            {
                "schema": "btrack_hypothesis_prophecy_v1",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "ts_utc": "2026-04-06T00:00:00Z",
                "label": "[HYPO] test",
                "prediction": {"instrument": "none", "horizon": "1d", "direction": "abstain"},
            }
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [sys.executable, str(_SCRIPT), "--validate-only", str(p)],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr


def test_bridge_adjustment_changes_confidence_when_context_removed() -> None:
    if not _BUNDLE.is_file():
        import pytest

        pytest.skip("bundle not built; run build_btrack_llm_input_bundle.py first")

    with tempfile.TemporaryDirectory(prefix="bridge_adj_test_") as td:
        tdp = Path(td)
        on_out = tdp / "hyp_on.json"
        off_out = tdp / "hyp_off.json"
        off_bundle = tdp / "bundle_off.json"

        bundle_doc = json.loads(_BUNDLE.read_text(encoding="utf-8"))
        arts = bundle_doc.get("artifacts")
        if isinstance(arts, dict):
            arts.pop("compression_bridge_context", None)
        paths = bundle_doc.get("artifact_paths")
        if isinstance(paths, dict):
            paths.pop("compression_kpi_summary", None)
            paths.pop("compression_active_report", None)
            paths.pop("compression_decision", None)
        off_bundle.write_text(json.dumps(bundle_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        cp_on = subprocess.run(
            [sys.executable, str(_SCRIPT), "--bundle", str(_BUNDLE), "--output", str(on_out)],
            capture_output=True,
            text=True,
        )
        assert cp_on.returncode == 0, cp_on.stderr
        cp_off = subprocess.run(
            [sys.executable, str(_SCRIPT), "--bundle", str(off_bundle), "--output", str(off_out)],
            capture_output=True,
            text=True,
        )
        assert cp_off.returncode == 0, cp_off.stderr

        on_doc = json.loads(on_out.read_text(encoding="utf-8"))
        off_doc = json.loads(off_out.read_text(encoding="utf-8"))
        on_meta = on_doc.get("runtime_meta") if isinstance(on_doc.get("runtime_meta"), dict) else {}
        off_meta = off_doc.get("runtime_meta") if isinstance(off_doc.get("runtime_meta"), dict) else {}
        on_adj = on_meta.get("compression_bridge_adjustment") if isinstance(on_meta.get("compression_bridge_adjustment"), dict) else {}
        off_adj = off_meta.get("compression_bridge_adjustment") if isinstance(off_meta.get("compression_bridge_adjustment"), dict) else {}

        assert on_meta.get("compression_bridge_available") is True
        assert off_meta.get("compression_bridge_available") is False
        assert bool(on_adj.get("applied")) is True
        assert bool(off_adj.get("applied")) is False
        assert on_doc.get("prediction", {}).get("direction") == off_doc.get("prediction", {}).get("direction")
        assert float(on_doc.get("prediction", {}).get("confidence")) != float(
            off_doc.get("prediction", {}).get("confidence")
        )


def test_research_kospi_uses_kospi_price_lens(tmp_path: Path) -> None:
    if not _BUNDLE.is_file():
        import pytest

        pytest.skip("bundle not built")
    kospi_csv = _ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
    if not kospi_csv.is_file():
        import pytest

        pytest.skip("kospi csv missing")
    out = tmp_path / "hyp_kospi.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--bundle",
            str(_BUNDLE),
            "--output",
            str(out),
            "--research-evaluation-instrument",
            "kospi",
        ],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("prediction", {}).get("instrument") == "kospi"
    runtime_meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
    assert runtime_meta.get("price_instrument") == "kospi"
    price_meta = runtime_meta.get("price_meta") if isinstance(runtime_meta.get("price_meta"), dict) else {}
    assert price_meta.get("instrument") == "kospi"
    assert price_meta.get("reason") != "score_rows_missing"
