from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "projects/mkm/mkm-life/scripts/Deploy-CloudflareMkmlife.ps1"


def test_mkmlife_deploy_preflight_dev_stop_and_open_next_cleanup() -> None:
    text = DEPLOY.read_text(encoding="utf-8")
    assert "SkipDevServerStop" in text
    assert "SkipRestartDevAfterDeploy" in text
    assert "Stop-MkmlifeLocalDevForDeploy" in text
    assert "Start-MkmlifeDesignPortalDevAfterDeploy" in text
    assert "Clear-MkmlifeOpenNextOutput" in text
    assert "Get-MkmlifeDevListenPort" in text
    assert "oracle-sphere-live-dev-runner" in text
    assert "open-next-stale-" in text
    assert "Assert-MkmlifeDeployTokenIsolation" in text
    assert "generic CLOUDFLARE_API_TOKEN/CF_API_TOKEN must not deploy mkmlife" in text
    assert "AllowGenericCloudflareToken" in text
