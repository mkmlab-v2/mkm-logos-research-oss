from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_web_ops_regime_gate_v1.py"
CHECK = ROOT / "scripts" / "check_web_ops_regime_gate_v1.py"
CDP_PROBE = ROOT / "scripts" / "run_web_ops_regime_cdp_probe_v1.py"
FULL_BUNDLE = ROOT / "scripts" / "run_web_ops_regime_full_bundle_v1.py"
SYNC_BASELINES = ROOT / "scripts" / "sync_web_ops_regime_pointer_baselines_v1.py"
CLASSIFIER = ROOT / "scripts" / "web_ops_regime_classifier_v1.py"


def test_classifier_payment_hold() -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.web_ops_regime_classifier_v1 import classify_regime

    out = classify_regime(
        url="https://console.nebius.com/billing/payments",
        body_text="Add payment method Connect card",
        hints={"billing_setup_needed": True, "payment_configured": False},
        human_gate="nebius_payment_card_tier3",
    )
    assert out["regime_id"] == "payment_risk"
    assert out["final_action"] == "HOLD_PAYMENT"


def test_is_auth_wall_observation() -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.web_ops_regime_classifier_v1 import is_auth_wall_observation

    assert is_auth_wall_observation({"url": "https://auth.nebius.com/ui/login", "body_primary": "Welcome"})
    assert not is_auth_wall_observation(
        {
            "url": "https://console.nebius.com/tenant/billing/payments",
            "body_primary": "Active Balance $25.00",
        }
    )


def test_classifier_read_only_active_balance() -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.web_ops_regime_classifier_v1 import classify_regime

    out = classify_regime(
        url="https://console.nebius.com/billing/payments",
        body_text="Active Balance $25.00 Ending balance Consumption $0.00 Limits Quotas H200",
        hints={"payment_configured": True, "balance_usd": 25.0},
    )
    assert out["regime_id"] == "read_only_dashboard"
    assert out["final_action"] == "ALLOW_READ"


def test_azure_feasibility_not_auth_wall() -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.web_ops_regime_classifier_v1 import classify_regime

    out = classify_regime(
        url="https://portal.azure.com/",
        body_text="GPU VM quota limit=0 until Microsoft approves support ticket 2606030030000175",
        hints={"feasibility_report": True, "artifact_read_only": True, "payment_configured": True},
    )
    assert out["regime_id"] == "read_only_dashboard"
    assert out["final_action"] == "ALLOW_READ"


def test_build_and_check_bundle(tmp_path: Path) -> None:
    nebius = {
        "project_url": "https://console.nebius.com/project-x",
        "billing_url": "https://console.nebius.com/billing/payments",
        "console_title": "default-project-eu-north1",
        "billing_snippet": "Active Balance $25.00 Consumption $0.00 Limits Quotas",
        "billing_payment_configured": True,
        "balance_usd": 25.0,
        "billing_complete": True,
    }
    azure = {
        "subscription_name": "MKM-Startups-Prod",
        "gpu_vm_feasible_now": False,
        "gpu_vm_blocker": "GPU VM quota limit=0",
        "credits": {"usd_remaining_env": "1000"},
    }
    neb_path = tmp_path / "nebius.json"
    az_path = tmp_path / "azure.json"
    out_path = tmp_path / "gate.json"
    neb_path.write_text(json.dumps(nebius), encoding="utf-8")
    az_path.write_text(json.dumps(azure), encoding="utf-8")

    cp_build = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--nebius-json",
            str(neb_path),
            "--nebius-benefit-json",
            str(neb_path),
            "--azure-json",
            str(az_path),
            "--out",
            str(out_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_build.returncode == 0, cp_build.stderr

    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["schema"] == "web_ops_regime_gate_v1"
    assert doc["gate_pass"] is True
    assert doc["conflict_resolver"]["worst_final_action"] == "ALLOW_READ"
    assert len(doc["probes"]) == 2

    cp_check = subprocess.run(
        [sys.executable, str(CHECK), "--in-json", str(out_path), "--require-gate-pass"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_check.returncode == 0, cp_check.stdout + cp_check.stderr


def test_dual_observation_match_and_mismatch() -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.web_ops_regime_classifier_v1 import dual_observation_gate, probe_from_live_observation

    body = "Active Balance $25.00 Consumption $0.00 Limits Quotas H200 H100"
    dual_ok = dual_observation_gate(body_primary=body, body_secondary=body, min_similarity=0.72)
    assert dual_ok["alignment_pass"] is True

    dual_bad = dual_observation_gate(
        body_primary=body,
        body_secondary="Sign in with Microsoft password oauth",
        min_similarity=0.72,
    )
    assert dual_bad["alignment_pass"] is False

    probe = probe_from_live_observation(
        probe_id="cdp_live_tab",
        portal="nebius",
        url="https://console.nebius.com/billing/payments",
        title="billing",
        body_primary=body,
        body_secondary=body,
        hints={"payment_configured": True, "balance_usd": 25.0},
    )
    assert probe["final_action"] == "ALLOW_READ"
    assert probe["dual_observation"]["alignment_pass"] is True


def test_pointer_drift_hold() -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.web_ops_regime_classifier_v1 import page_fingerprint, probe_from_live_observation

    body = "Active Balance $25.00 Consumption $0.00"
    url = "https://console.nebius.com/billing/payments"
    fp = page_fingerprint(url=url, anchor_strings=["billing", url, "balance"])
    baselines = {"nebius:cdp_live_tab": {"page_fingerprint": "deadbeef00000000"}}

    probe = probe_from_live_observation(
        probe_id="cdp_live_tab",
        portal="nebius",
        url=url,
        title="billing",
        body_primary=body,
        body_secondary=body,
        hints={"payment_configured": True},
        baselines=baselines,
    )
    assert probe["pointer_drift"]["drift_detected"] is True
    assert probe["final_action"] == "HOLD_POINTER_DRIFT"
    assert fp != "deadbeef00000000"


def test_cdp_probe_dry_run_and_baseline_sync(tmp_path: Path) -> None:
    obs = {
        "url": "https://console.nebius.com/billing/payments",
        "title": "default-project",
        "body_primary": "Active Balance $25.00 Consumption $0.00 Limits Quotas",
        "body_secondary": "Active Balance $25.00 Consumption $0.00 Limits Quotas",
        "hints": {"payment_configured": True, "balance_usd": 25.0},
    }
    obs_path = tmp_path / "obs.json"
    out_path = tmp_path / "cdp_probe.json"
    baseline_path = tmp_path / "baselines.json"
    obs_path.write_text(json.dumps(obs), encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(CDP_PROBE),
            "--dry-run-from-json",
            str(obs_path),
            "--out",
            str(out_path),
            "--no-refresh-gate",
            "--baselines-json",
            str(baseline_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["probe"]["final_action"] == "ALLOW_READ"

    cp_sync = subprocess.run(
        [
            sys.executable,
            str(SYNC_BASELINES),
            "--cdp-json",
            str(out_path),
            "--gate-json",
            str(out_path),
            "--out",
            str(baseline_path),
            "--seed",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_sync.returncode == 0, cp_sync.stderr
    baselines = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert "nebius:cdp_live_tab" in baselines["baselines"]


def test_write_live_observation_json(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.run_web_ops_regime_cdp_probe_v1 import write_live_observation_json

    obs = {
        "url": "https://console.nebius.com/billing/payments",
        "title": "billing",
        "body_primary": "Balance $25.00",
        "body_secondary": "Balance $25.00",
        "hints": {"payment_configured": True},
    }
    out = tmp_path / "live.json"
    ide = tmp_path / "ide.json"
    import scripts.run_web_ops_regime_cdp_probe_v1 as mod

    old_ide = mod.DEFAULT_IDE_OBS
    mod.DEFAULT_IDE_OBS = ide
    try:
        path = write_live_observation_json(obs, out=out)
        assert path == out
        assert json.loads(out.read_text(encoding="utf-8"))["body_primary"] == "Balance $25.00"
        assert ide.is_file()
    finally:
        mod.DEFAULT_IDE_OBS = old_ide


def test_health_summary_builder(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.build_web_ops_regime_health_summary_v1 import build_summary

    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "gate_pass": True,
                "conflict_resolver": {"worst_final_action": "ALLOW_READ", "probe_count": 2},
                "cost_policy": {"no_gpu_spinup": True},
                "operator_hint_ko": "ok",
            }
        ),
        encoding="utf-8",
    )
    cdp = tmp_path / "cdp.json"
    cdp.write_text(
        json.dumps(
            {
                "observation_source": "dry_run_json",
                "probe": {
                    "dual_observation": {"alignment_pass": True},
                    "pointer_drift": {"drift_detected": False},
                    "raw": {"balance_usd": 25.0},
                },
            }
        ),
        encoding="utf-8",
    )
    baselines = tmp_path / "baselines.json"
    baselines.write_text(json.dumps({"baselines": {"nebius:cdp_live_tab": {}}}), encoding="utf-8")
    live_obs = tmp_path / "live.json"
    live_obs.write_text(json.dumps({"url": "https://console.nebius.com/billing/payments"}), encoding="utf-8")
    import scripts.build_web_ops_regime_health_summary_v1 as mod

    old = (mod.GATE, mod.CDP, mod.BASELINES, mod.LIVE_OBS, mod.GPU_DOD)
    mod.GATE = gate
    mod.CDP = cdp
    mod.BASELINES = baselines
    mod.LIVE_OBS = live_obs
    mod.GPU_DOD = tmp_path / "missing_gpu_dod.json"
    try:
        doc = build_summary()
        assert doc["health_ok"] is True
        assert doc["gate_pass"] is True
        assert doc["schema"] == "web_ops_regime_health_summary_v1"
    finally:
        mod.GATE, mod.CDP, mod.BASELINES, mod.LIVE_OBS, mod.GPU_DOD = old


def test_cdp_probe_from_nebius_portal_json(tmp_path: Path) -> None:
    nebius = {
        "project_url": "https://console.nebius.com/project-x",
        "billing_url": "https://console.nebius.com/tenant-x/billing/consumption",
        "console_title": "default-project",
        "billing_snippet": "Manage Billing Payments Limits Quotas",
        "setup_ok": True,
        "gpu_limits_mentioned": ["H200", "H100"],
    }
    benefit = {
        "billing_complete": True,
        "balance_usd": 25.0,
        "console": {"payments_url": "https://console.nebius.com/tenant-x/billing/payments"},
    }
    neb_path = tmp_path / "nebius.json"
    ben_path = tmp_path / "benefit.json"
    out_path = tmp_path / "cdp.json"
    baseline_path = tmp_path / "baselines.json"
    neb_path.write_text(json.dumps(nebius), encoding="utf-8")
    ben_path.write_text(json.dumps(benefit), encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(CDP_PROBE),
            "--from-nebius-json",
            str(neb_path),
            "--from-nebius-benefit-json",
            str(ben_path),
            "--baselines-json",
            str(baseline_path),
            "--out",
            str(out_path),
            "--no-refresh-gate",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["observation_source"] == "portal_json_derived"
    assert doc["probe"]["final_action"] == "ALLOW_READ"


def test_full_bundle_offline(tmp_path: Path) -> None:
    nebius = {
        "project_url": "https://console.nebius.com/project-x",
        "billing_url": "https://console.nebius.com/tenant-x/billing/payments",
        "console_title": "default-project",
        "billing_snippet": "Payments Limits Quotas H200",
        "setup_ok": True,
    }
    benefit = {"billing_complete": True, "balance_usd": 25.0}
    azure = {
        "subscription_name": "MKM",
        "gpu_vm_feasible_now": False,
        "gpu_vm_blocker": "GPU VM quota limit=0",
        "credits": {"usd_remaining_env": "1000"},
    }
    neb_path = tmp_path / "nebius.json"
    az_path = tmp_path / "azure.json"
    ben_path = tmp_path / "benefit.json"
    neb_path.write_text(json.dumps(nebius), encoding="utf-8")
    ben_path.write_text(json.dumps(benefit), encoding="utf-8")
    az_path.write_text(json.dumps(azure), encoding="utf-8")

    # Point default nebius path via env override — full bundle uses fixed paths.
    # Run components manually with tmp outputs instead.
    cdp_out = tmp_path / "cdp.json"
    gate_out = tmp_path / "gate.json"
    baselines_out = tmp_path / "baselines.json"

    cp1 = subprocess.run(
        [
            sys.executable,
            str(CDP_PROBE),
            "--from-nebius-json",
            str(neb_path),
            "--from-nebius-benefit-json",
            str(ben_path),
            "--out",
            str(cdp_out),
            "--gate-out",
            str(gate_out),
            "--baselines-json",
            str(baselines_out),
            "--no-refresh-gate",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp1.returncode == 0, cp1.stderr

    cp_build = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--nebius-json",
            str(neb_path),
            "--nebius-benefit-json",
            str(ben_path),
            "--azure-json",
            str(az_path),
            "--cdp-probe-json",
            str(cdp_out),
            "--out",
            str(gate_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_build.returncode == 0, cp_build.stderr
    gate = json.loads(gate_out.read_text(encoding="utf-8"))
    assert gate["gate_pass"] is True
    assert gate["conflict_resolver"]["probe_count"] == 3
