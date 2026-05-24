# Phase 2: CF zone finalize poll, DNS ensure, VPS sync, readiness report, probe.
param(
    [int]$ActivationPolls = 4,
    [int]$PollSleepSec = 25
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$steps = [System.Collections.Generic.List[object]]::new()

function Step($n, $code, $detail) {
    $steps.Add([ordered]@{ step = $n; exit_code = [int]$code; detail = $detail }) | Out-Null
}

& py (Join-Path $root "scripts\finalize_mkmlab_cloudflare_zone_v1.py") --polls $ActivationPolls --sleep-s $PollSleepSec
Step "cf_zone_finalize" $LASTEXITCODE "activation + edge settings"

& py (Join-Path $root "scripts\prune_mkmlab_cloudflare_dns_v1.py")
Step "cf_dns_prune" $LASTEXITCODE "stray A/AAAA"

& py (Join-Path $root "scripts\ensure_mkmlab_space_cloudflare_dns_v1.py") --origin-ip 148.230.97.246 --zone-id 38a47f29983bd4ebce3798be08f59ba3
Step "cf_dns_ensure" $LASTEXITCODE "apex+www"

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Sync-MkmlabRedesignToVps_v1.ps1")
Step "vps_sync" $LASTEXITCODE "full tree"

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-MkmlabSpaceDeployReadiness_v1.ps1") -ApplyCloudflare
Step "deploy_readiness" $LASTEXITCODE "report+json"

$worst = ($steps | ForEach-Object { $_.exit_code } | Measure-Object -Maximum).Maximum
$out = Join-Path $root "reports\mkmlab_space_phase2_latest.json"
[ordered]@{
    schema           = "mkmlab_space_phase2_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    worst_exit       = [int]$worst
    steps            = @($steps)
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "Wrote $out worst_exit=$worst"
exit $worst
