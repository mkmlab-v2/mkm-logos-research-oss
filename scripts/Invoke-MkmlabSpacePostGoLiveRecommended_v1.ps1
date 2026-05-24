# Post go-live recommended: mkmlab VPS sync, probe, optional jema-ai hub deploy (research_mkmlab link).
param(
    [switch]$SkipJemaAiDeploy,
    [switch]$DryRunJemaAi
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$steps = [System.Collections.Generic.List[object]]::new()

function Step($n, $code, $detail) {
    $steps.Add([ordered]@{ step = $n; exit_code = [int]$code; detail = $detail }) | Out-Null
}

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Sync-MkmlabRedesignToVps_v1.ps1")
Step "mkmlab_vps_sync" $LASTEXITCODE "mkmlab-redesign -> /var/www/mkmlab"

& py (Join-Path $root "scripts\probe_mkmlab_space_readiness_v1.py")
Step "mkmlab_probe" $LASTEXITCODE "https + en.html"

if (-not $SkipJemaAiDeploy) {
    $deployArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $root "scripts\Deploy-No1kmediDestinyTarball_v1.ps1")
    )
    if ($DryRunJemaAi) { $deployArgs += "-DryRun" }
    & powershell @deployArgs
    Step "jema_ai_hub_deploy" $LASTEXITCODE "public-copy research_mkmlab on jema-ai.com"
}

$worst = ($steps | ForEach-Object { $_.exit_code } | Measure-Object -Maximum).Maximum
$report = Join-Path $root "reports\mkmlab_space_post_golive_recommended_latest.json"
[ordered]@{
    schema           = "mkmlab_space_post_golive_recommended_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    worst_exit       = [int]$worst
    steps            = @($steps)
    notes            = @(
        "Channel split: mkmlab.space=research/products; B2B CTAs -> jema-ai.com/enterprise?source=mkmlab_space"
        "Cloudflare zone may stay pending; origin TLS on VPS is OK until CF proxy fully active"
    )
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $report -Encoding UTF8
Write-Host "Wrote $report worst_exit=$worst"
exit $worst
