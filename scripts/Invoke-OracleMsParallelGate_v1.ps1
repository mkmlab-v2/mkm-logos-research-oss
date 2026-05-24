#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot parallel gate: MS paste pack + Oracle live + O-P5 redirect + RQ-019 regression.
  Writes reports/oracle_ms_parallel_gate_latest.json
#>
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$out = Join-Path $root "reports\oracle_ms_parallel_gate_latest.json"
$steps = @{}
$errors = @()

function Invoke-Step {
    param([string]$Name, [scriptblock]$Block)
    try {
        & $Block
        $steps[$Name] = @{ ok = ($LASTEXITCODE -eq 0); exit_code = $LASTEXITCODE }
        if ($LASTEXITCODE -ne 0) { $script:errors += "$Name exit $LASTEXITCODE" }
    } catch {
        $steps[$Name] = @{ ok = $false; error = $_.Exception.Message }
        $script:errors += "$Name $($_.Exception.Message)"
    }
}

Push-Location $root
try {
    Invoke-Step "paste_pack_readiness" { & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-MsRq019PastePackReadiness_v1.ps1") }
    Invoke-Step "showroom_smoke" { & py (Join-Path $root "scripts\check_showroom_trust_viz_public_chain_v1.py") }
    Invoke-Step "jema12_studio_redirect" { & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\verify_jema12_studio_oracle_redirect_v1.ps1") }
    Invoke-Step "rq019_regression" { & py (Join-Path $root "scripts\run_mkm_inter_agent_rq019_regression_chain_v1.py") --skip-pytest }
    Invoke-Step "ms_auto_status" { & py (Join-Path $root "scripts\build_ms_rq019_auto_status_v1.py") }
    Invoke-Step "cf_studio_dry_run" { & py (Join-Path $root "scripts\setup_cloudflare_jema12_studio_oracle_redirect_v1.py") --dry-run }
} finally { Pop-Location }

$doc = @{
    schema = "oracle_ms_parallel_gate_v1"
    checked_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    steps = $steps
    ok = ($errors.Count -eq 0)
    errors = $errors
    commander_blockers = @()
}
if (-not $steps["jema12_studio_redirect"].ok) {
    $doc.commander_blockers += "O-P5: op5_cloudflare_studio_manual.txt OR op5_jema12_nginx_one_liner.txt"
}
if ($steps["paste_pack_readiness"].ok) {
    $doc.commander_next = @("MS paste 1-7 from reports/ms_rq019_paste_ready/", "Attach ms_rq019_oracle_v5_visual_path_10s.gif to K3")
}

New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
$doc | ConvertTo-Json -Depth 6 | Set-Content -Path $out -Encoding UTF8

Write-Host "== oracle_ms_parallel_gate ==" -ForegroundColor Cyan
Write-Host "ok=$($doc.ok) steps=$($steps.Count) errors=$($errors.Count)"
Write-Host "Wrote $out"
exit $(if ($doc.ok) { 0 } else { 1 })
