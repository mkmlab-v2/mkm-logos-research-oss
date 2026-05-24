#Requires -Version 5.1
<#
.SYNOPSIS
  jemaai.cloud showroom edge: try API apply + smoke + probe + CF probe.
#>
param(
    [switch]$SkipApply,
    [switch]$SkipVpsSync
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $SkipApply) {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & py scripts/check_jemaai_cloud_cf_rules_token_v1.py *> $null
    $rulesCheckExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($rulesCheckExit -ne 0) {
        Write-Host "[autoverify] rulesets token not automation_ready — skip API apply (no 403 spam)" -ForegroundColor Yellow
        Write-Host "  Fix: Invoke-CloudflareJemaaiCfEdgeOneShot_v1.ps1 or JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md" -ForegroundColor Yellow
        $SkipApply = $true
    }
}
if (-not $SkipApply) {
    py scripts/apply_jemaai_cloud_showroom_cf_edge_rules_v1.py
    $applyExit = $LASTEXITCODE
} else {
    $applyExit = -1
}

py scripts/check_showroom_trust_viz_public_chain_v1.py
$smokeExit = $LASTEXITCODE

# Low-rate probe only (not_media_scale); avoids CF rate-limit 429 after rules apply.
py scripts/build_showroom_static_load_probe_v1.py --requests 5 --workers 2
$probeExit = $LASTEXITCODE

py scripts/ensure_jemaai_cloud_cf_edge_hardening_v1.py | Out-Null
$cfExit = $LASTEXITCODE

if (-not $SkipVpsSync) {
    powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/sync_showroom_to_vps.ps1 -NginxSnippetOnly -ApplyRecommendedNginx | Out-Null
    $syncExit = $LASTEXITCODE
} else {
    $syncExit = -1
}

if ($applyExit -lt 0) {
    py scripts/check_jemaai_cloud_cf_rules_token_v1.py | Out-Null
    $cfRulesOk = ($LASTEXITCODE -eq 0)
} else {
    $cfRulesOk = ($applyExit -eq 0)
}
$infraOk = ($smokeExit -eq 0 -and $probeExit -eq 0 -and $cfRulesOk)
$summary = [ordered]@{
    schema = "jemaai_showroom_edge_autoverify_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    apply_exit = $applyExit
    smoke_exit = $smokeExit
    probe_exit = $probeExit
    cf_probe_exit = $cfExit
    sync_exit = $syncExit
    cf_rules_api_ok = $cfRulesOk
    infra_ok = $infraOk
}
$outPath = Join-Path $Root "reports/jemaai_showroom_edge_autoverify_v1_latest.json"
$summary | ConvertTo-Json -Depth 5 | Set-Content -Path $outPath -Encoding UTF8
Write-Host "[autoverify] apply=$applyExit smoke=$smokeExit probe=$probeExit cf=$cfExit sync=$syncExit -> $outPath"
if ($smokeExit -ne 0) { exit $smokeExit }
if ($probeExit -ne 0) { exit $probeExit }
exit 0
