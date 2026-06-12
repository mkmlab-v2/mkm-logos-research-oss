#Requires -Version 5.1
<#
.SYNOPSIS
  MKM 멀티도메인 디자인 레인 일단락 — 오프라인 게이트 + 라이브 스모크 + closure JSON.

.DESCRIPTION
  mkmlife.com · jema-ai.com · jemaai.cloud · personadiary.com 디자인 허브·Phase 2 프리뷰
  (personadiary = preview_only · [HYPO]) 검증. Track A·실매매·DB 합선 없음.

  순서:
  1) verify_p0_constitution_gate_paths.ps1
  2) check_mkm_domain_design_tokens_v1.py
  3) domain design offline pytest (tokens · personadiary · mkmlife facade)
  4) mkmlife live smoke (-SkipBuild; optional Playwright)
  5) personadiary live smoke
  6) jemaai.cloud showroom hub footer live smoke

  판정: `reports/mkm_domain_design_closure_v1_latest.json` 의 `closure_ok: true`

.PARAMETER SkipLiveSmoke
  4–6단계 라이브 스모크 생략(오프라인만).

.PARAMETER SkipPlaywright
  mkmlife Playwright skim 생략.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmDomainDesignClosureBundle_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipLiveSmoke,
    [switch]$SkipPlaywright
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $WorkspaceRoot

$reportPath = Join-Path $WorkspaceRoot "reports\mkm_domain_design_closure_v1_latest.json"
$steps = [System.Collections.Generic.List[object]]::new()
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$closureOk = $false
$failureMessage = $null

function Add-Step([string]$Name, $ExitCode) {
    $script:steps.Add([ordered]@{ name = $Name; exit_code = $ExitCode }) | Out-Null
}

function Invoke-BundleScript([string]$RelPath, [string[]]$ScriptArguments) {
    $full = Join-Path $WorkspaceRoot $RelPath
    if (-not (Test-Path -LiteralPath $full)) { throw "Missing script: $full" }
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $full) + $ScriptArguments
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -WorkingDirectory $WorkspaceRoot `
        -Wait -PassThru -NoNewWindow
    return [int]$p.ExitCode
}

$offlinePytests = @(
    "tests/test_check_mkm_domain_design_tokens_v1.py",
    "tests/test_check_mkm_ui_shell_contract_v1.py",
    "tests/test_check_mkm_universe_hub_shell_v2.py",
    "tests/test_personadiary_ritual_draw_lut_v1.py",
    "tests/test_personadiary_lattice_convergence_v1.py",
    "tests/test_personadiary_live_ops_smoke_v1.py",
    "tests/test_check_mkmlife_portal_commercialization_gate_v1.py",
    "tests/test_build_mkmlife_news_observation_deck_v1.py",
    "tests/test_mkmlife_skim_read_preference_v1.py",
    "tests/test_mkm_consumer_facade_v1.py"
)

try {
    $e0 = Invoke-BundleScript "scripts\verify_p0_constitution_gate_paths.ps1" @()
    Add-Step "verify_p0" $e0
    if ($e0 -ne 0) { throw "verify_p0 failed exit $e0" }

    & py scripts/check_mkm_domain_design_tokens_v1.py
    $e1 = $LASTEXITCODE
    Add-Step "check_mkm_domain_design_tokens" $e1
    if ($e1 -ne 0) { throw "check_mkm_domain_design_tokens failed exit $e1" }

    & py scripts/check_mkm_ui_shell_contract_v1.py
    $e1b = $LASTEXITCODE
    Add-Step "check_mkm_ui_shell_contract" $e1b
    if ($e1b -ne 0) { throw "check_mkm_ui_shell_contract failed exit $e1b" }

    & py scripts/check_mkm_universe_hub_shell_v2.py
    $e1c = $LASTEXITCODE
    Add-Step "check_mkm_universe_hub_shell_v2" $e1c
    if ($e1c -ne 0) { throw "check_mkm_universe_hub_shell_v2 failed exit $e1c" }

    Write-Host "== domain design offline pytest ==" -ForegroundColor Cyan
    & py -m pytest @offlinePytests -q --tb=short
    $e2 = $LASTEXITCODE
    Add-Step "domain_design_offline_pytest" $e2
    if ($e2 -ne 0) { throw "domain_design_offline_pytest failed exit $e2" }

    if (-not $SkipLiveSmoke) {
        $mkArgs = @("-SkipBuild", "-SkipPytest", "-IncludeLiveSmoke")
        if (-not $SkipPlaywright) {
            $mkArgs += "-IncludePlaywright", "-StrictPlaywright"
        }
        $e3 = Invoke-BundleScript "scripts\Run-MkmlifePortalCommercializationGate_v1.ps1" $mkArgs
        Add-Step "mkmlife_portal_live_smoke" $e3
        if ($e3 -ne 0) { throw "mkmlife_portal_live_smoke failed exit $e3" }

        $e4 = Invoke-BundleScript "scripts\Run-PersonadiaryPortalDesignSmoke_v1.ps1" @()
        Add-Step "personadiary_portal_design_live" $e4
        if ($e4 -ne 0) { throw "personadiary_portal_design_live failed exit $e4" }

        $e5 = Invoke-BundleScript "scripts\Run-JemaaiShowroomHubFooterLiveSmoke_v1.ps1" @()
        Add-Step "jemaai_showroom_hub_footer_live" $e5
        if ($e5 -ne 0) { throw "jemaai_showroom_hub_footer_live failed exit $e5" }
    }
    else {
        Add-Step "live_smokes_skipped" $null
    }

    $closureOk = $true
}
catch {
    $closureOk = $false
    $failureMessage = $_.Exception.Message
    Write-Warning "mkm domain design closure failed: $failureMessage"
}

$out = [ordered]@{
    schema            = "mkm_domain_design_closure_v1"
    generated_at_utc  = $ts
    workspace_root    = $WorkspaceRoot
    closure_ok        = $closureOk
    scope             = "multi_domain_design_preview_only_no_track_a_no_live_trading"
    domains           = @("mkmlife.com", "jema-ai.com", "jemaai.cloud", "personadiary.com")
    personadiary_lane = "preview_only_hypo_b_track"
    track_wall        = "no_track_a_promotion_no_live_trading_no_mkmlife_api_db_merge"
    steps             = $steps
    failure_message   = $failureMessage
    ssot              = @(
        "docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md",
        "docs/final/artifacts/mkm_domain_design_tokens_v1.json",
        "docs/final/artifacts/mkm_ui_shell_contract_v1.json",
        "docs/final/PERSONADIARY_DOMAIN_POINTER_V1.md"
    )
    notes             = "UI polish pass closure; re-run after domain deploy or hub footer changes."
}

$parent = Split-Path -Parent $reportPath
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
$out | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "[DONE] Wrote $reportPath (closure_ok=$closureOk)" -ForegroundColor $(if ($closureOk) { 'Green' } else { 'Red' })
if (-not $closureOk) { exit 1 }
exit 0
