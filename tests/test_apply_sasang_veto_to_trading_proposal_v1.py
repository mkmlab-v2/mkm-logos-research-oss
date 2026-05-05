from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apply_sasang_veto_to_trading_proposal_smoke(tmp_path: Path) -> None:
    proposal = {
        "schema": "trading_execution_proposal_v1",
        "proposal_id": "p1",
        "order_intent": {"symbol": "BTCUSDT", "side": "BUY", "qty": 0.01},
    }
    veto = {
        "schema": "sasang_veto_only_active_config_v1",
        "enabled": True,
        "scope": "veto_only_non_directional",
        "soft_exposure": 0.8,
        "hard_guardrails": {"directional_entry_disabled": True, "auto_bridge_allowed": False},
    }
    proposal_path = tmp_path / "proposal.json"
    veto_path = tmp_path / "veto.json"
    out = tmp_path / "out.json"
    proposal_path.write_text(json.dumps(proposal, ensure_ascii=False) + "\n", encoding="utf-8")
    veto_path.write_text(json.dumps(veto, ensure_ascii=False) + "\n", encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "apply_sasang_veto_to_trading_proposal_v1.py"),
            "--proposal-json",
            str(proposal_path),
            "--veto-config-json",
            str(veto_path),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "trading_execution_proposal_veto_adjusted_v1"
    assert doc.get("veto_applied") is True
    assert doc.get("veto_branch_id") == "legacy_top_level"
    assert abs(float(doc["order_adjustment"]["effective_qty"]) - 0.008) < 1e-12


def test_apply_sasang_veto_asset_branch_btc_vs_default(tmp_path: Path) -> None:
    proposal_btc = {
        "schema": "trading_execution_proposal_v1",
        "proposal_id": "p_btc",
        "order_intent": {"symbol": "BTCUSDT", "side": "BUY", "qty": 0.02},
    }
    proposal_eth = {
        "schema": "trading_execution_proposal_v1",
        "proposal_id": "p_eth",
        "order_intent": {"symbol": "ETHUSDT", "side": "BUY", "qty": 0.02},
    }
    veto = {
        "schema": "sasang_veto_only_active_config_v1",
        "enabled": True,
        "scope": "veto_only_non_directional",
        "soft_exposure": 1.0,
        "symbol_routing": {"ETHUSDT": "default"},
        "asset_branches": {
            "default": {"veto_set": ["soeum"], "soft_exposure": 0.25, "params": {"adx_cut": 20.0}},
            "BTCUSDT": {"veto_set": ["soeum"], "soft_exposure": 0.5, "params": {"adx_cut": 24.0}},
        },
        "hard_guardrails": {"directional_entry_disabled": True, "auto_bridge_allowed": False},
    }
    base = tmp_path / "veto.json"
    base.write_text(json.dumps(veto, ensure_ascii=False) + "\n", encoding="utf-8")

    out_b = tmp_path / "out_btc.json"
    out_e = tmp_path / "out_eth.json"
    pb = tmp_path / "proposal_btc.json"
    pe = tmp_path / "proposal_eth.json"
    pb.write_text(json.dumps(proposal_btc, ensure_ascii=False) + "\n", encoding="utf-8")
    pe.write_text(json.dumps(proposal_eth, ensure_ascii=False) + "\n", encoding="utf-8")

    for prop, out in ((pb, out_b), (pe, out_e)):
        cp = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "apply_sasang_veto_to_trading_proposal_v1.py"),
                "--proposal-json",
                str(prop),
                "--veto-config-json",
                str(base),
                "--out-json",
                str(out),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert cp.returncode == 0, cp.stderr

    doc_b = json.loads(out_b.read_text(encoding="utf-8"))
    doc_e = json.loads(out_e.read_text(encoding="utf-8"))
    assert doc_b.get("veto_branch_id") == "BTCUSDT"
    assert doc_e.get("veto_branch_id") == "default"
    assert abs(float(doc_b["order_adjustment"]["effective_qty"]) - 0.01) < 1e-12
    assert abs(float(doc_e["order_adjustment"]["effective_qty"]) - 0.005) < 1e-12

