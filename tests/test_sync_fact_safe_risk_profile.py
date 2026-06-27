import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.sync_fact_safe_risk_profile import _derive_profile, _would_downgrade_n8n_metadata

_SYNC_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_fact_safe_risk_profile.py"
_MARKET_PULSE_FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "market_pulse_tactical_v1.json"


def test_derive_profile_stamps_logos_non_gating_ack():
    out = _derive_profile(
        risk_profile={
            "mode": "LOCKED_MODE",
            "logos_regime_score": 0.5,
            "position_scale_cap": 0.2,
            "daily_loss_cap_pct": 1.0,
            "fused_risk_pressure": 0.6,
        },
        now=datetime.now(timezone.utc),
        source_name="repo.fact_safe_sync.v1",
        mode_name="repo_shadow",
    )
    tg = out["trinity_governor"]
    assert tg["logos_non_gating_ack"] is True
    assert "NON_GATING" in tg["governance_note"]


def test_would_downgrade_n8n_metadata():
    assert not _would_downgrade_n8n_metadata({}, "fact_safe_prophecy.trinity_governor")
    assert not _would_downgrade_n8n_metadata({"source": "fact_safe_prophecy.trinity_governor"}, "n8n.regime_watch.v5")
    assert _would_downgrade_n8n_metadata({"source": "n8n.regime_watch.v5"}, "fact_safe_prophecy.trinity_governor")
    assert not _would_downgrade_n8n_metadata({"source": "n8n.regime_watch.v5"}, "n8n.regime_watch.v5")


def test_derive_profile_locked_mode_enforces_hard_limits():
    out = _derive_profile(
        risk_profile={
            "mode": "LOCKED_MODE",
            "position_scale_cap": 0.2,
            "daily_loss_cap_pct": 0.7,
            "fused_risk_pressure": 0.9,
        },
        now=datetime.now(timezone.utc),
        source_name="fact_safe_prophecy.trinity_governor",
        mode_name="shadow",
    )
    assert out["max_trades_per_day"] == 4
    assert out["max_position_size"] == 0.03
    assert out["maker_only_level"] == "strict"
    assert out["kill_switch_threshold"] == 0.015
    assert out["singular_core"]["core_decision"] == "HOLD"


def test_derive_profile_active_mode_maps_to_bounded_fields():
    out = _derive_profile(
        risk_profile={
            "mode": "ACTIVE_MODE",
            "position_scale_cap": 0.5,
            "daily_loss_cap_pct": 1.2,
            "fused_risk_pressure": 0.6,
        },
        now=datetime.now(timezone.utc),
        source_name="fact_safe_prophecy.trinity_governor",
        mode_name="shadow",
    )
    assert 4 <= out["max_trades_per_day"] <= 80
    assert 0.03 <= out["max_position_size"] <= 0.20
    assert out["maker_only_level"] == "preferred"
    assert 3 <= out["slippage_cap_bps"] <= 15
    assert 0.015 <= out["kill_switch_threshold"] <= 0.04


def test_derive_profile_forces_lock_when_core_hold():
    out = _derive_profile(
        risk_profile={
            "mode": "ACTIVE_MODE",
            "core_decision": "HOLD",
            "core_score": 0.25,
            "position_scale_cap": 0.9,
            "daily_loss_cap_pct": 2.0,
            "fused_risk_pressure": 0.2,
        },
        now=datetime.now(timezone.utc),
        source_name="fact_safe_prophecy.trinity_governor",
        mode_name="shadow",
    )
    assert out["max_trades_per_day"] == 4
    assert out["max_position_size"] == 0.03


def test_derive_profile_applies_integrated_governance_caps():
    out = _derive_profile(
        risk_profile={
            "mode": "ACTIVE_MODE",
            "position_scale_cap": 1.0,
            "daily_loss_cap_pct": 1.0,
            "fused_risk_pressure": 0.4,
        },
        now=datetime.now(timezone.utc),
        source_name="fact_safe_prophecy.trinity_governor",
        mode_name="shadow",
        governance={
            "schema": "integrated_governance_v1",
            "final_regime": "DEFENSE",
            "is_fallback": True,
            "final_action_allowed": False,
            "final_score": -0.72,
            "veto_reason_codes": ["extreme_defense_score"],
        },
    )
    assert out["governance_bridge"]["enabled"] is True
    assert out["governance_bridge"]["final_regime"] == "DEFENSE"
    assert out["governance_bridge"]["position_cap_multiplier"] <= 0.35
    assert out["leverage_multiplier_cap"] <= 0.5
    assert out["max_position_size"] <= 0.035


def _run_sync_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SYNC_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def minimal_prophecy_path(tmp_path: Path) -> Path:
    p = tmp_path / "prophecy.json"
    p.write_text(
        json.dumps(
            {
                "risk_profile": {
                    "mode": "LOCKED_MODE",
                    "core_decision": "HOLD",
                    "core_score": 0.0,
                    "core_contract_version": "mkm12_singular_core_v1",
                }
            }
        ),
        encoding="utf-8",
    )
    return p


def test_cli_refuses_n8n_metadata_downgrade(minimal_prophecy_path: Path, tmp_path: Path) -> None:
    out_path = tmp_path / "risk_profile.json"
    out_path.write_text(
        json.dumps({"source": "n8n.regime_watch.v5", "mode": "n8n_shadow"}),
        encoding="utf-8",
    )
    proc = _run_sync_cli(
        [
            "--prophecy",
            str(minimal_prophecy_path),
            "--output",
            str(out_path),
        ]
    )
    assert proc.returncode != 0
    assert "Refusing to overwrite n8n-tagged" in (proc.stderr or "")


def test_cli_allows_downgrade_with_flag(minimal_prophecy_path: Path, tmp_path: Path) -> None:
    out_path = tmp_path / "risk_profile.json"
    out_path.write_text(
        json.dumps({"source": "n8n.regime_watch.v5", "mode": "n8n_shadow"}),
        encoding="utf-8",
    )
    proc = _run_sync_cli(
        [
            "--prophecy",
            str(minimal_prophecy_path),
            "--output",
            str(out_path),
            "--allow-metadata-downgrade",
        ]
    )
    assert proc.returncode == 0
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["source"] == "fact_safe_prophecy.trinity_governor"


def test_cli_injects_market_pulse_from_json(minimal_prophecy_path: Path, tmp_path: Path) -> None:
    out_path = tmp_path / "risk_profile_market_pulse.json"
    proc = _run_sync_cli(
        [
            "--prophecy",
            str(minimal_prophecy_path),
            "--output",
            str(out_path),
            "--market-pulse-json",
            str(_MARKET_PULSE_FIXTURE),
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert "market_pulse" in written
    assert written["market_pulse"]["advance_decline_ratio"] == pytest.approx(1.18)
    assert written["market_pulse"]["foreign_net_buy_krw_eok"] == pytest.approx(29308.0)


def test_cli_market_pulse_overrides_are_applied(minimal_prophecy_path: Path, tmp_path: Path) -> None:
    out_path = tmp_path / "risk_profile_market_pulse_override.json"
    proc = _run_sync_cli(
        [
            "--prophecy",
            str(minimal_prophecy_path),
            "--output",
            str(out_path),
            "--market-pulse-json",
            str(_MARKET_PULSE_FIXTURE),
            "--market-theme-score",
            "0.92",
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["market_pulse"]["theme_leadership_score"] == pytest.approx(0.92)


def test_cli_repo_source_sets_repo_tags(minimal_prophecy_path: Path, tmp_path: Path) -> None:
    out_path = tmp_path / "risk_repo.json"
    proc = _run_sync_cli(
        [
            "--prophecy",
            str(minimal_prophecy_path),
            "--output",
            str(out_path),
            "--repo-source",
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["source"] == "repo.fact_safe_sync.v1"
    assert written["mode"] == "repo_shadow"


def test_cli_mutex_n8n_and_repo_source(minimal_prophecy_path: Path, tmp_path: Path) -> None:
    out_path = tmp_path / "risk_mutex.json"
    proc = _run_sync_cli(
        [
            "--prophecy",
            str(minimal_prophecy_path),
            "--output",
            str(out_path),
            "--n8n-source",
            "--repo-source",
        ]
    )
    assert proc.returncode != 0
    assert "mutually exclusive" in (proc.stderr or "")


def test_cli_repo_source_migrates_from_n8n_with_downgrade_flag(
    minimal_prophecy_path: Path, tmp_path: Path
) -> None:
    out_path = tmp_path / "risk_migrate.json"
    out_path.write_text(
        json.dumps({"source": "n8n.regime_watch.v5", "mode": "n8n_shadow"}),
        encoding="utf-8",
    )
    proc = _run_sync_cli(
        [
            "--prophecy",
            str(minimal_prophecy_path),
            "--output",
            str(out_path),
            "--repo-source",
            "--allow-metadata-downgrade",
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["source"] == "repo.fact_safe_sync.v1"
    assert written["mode"] == "repo_shadow"
