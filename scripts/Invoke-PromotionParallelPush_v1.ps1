#Requires -Version 5.1
<#
.SYNOPSIS
  승격 후보 병렬 밀기 — evidence·recommended chain·명리·사상·프리미엄·[HYPO] push (Track A/live/헤드라인 SSOT 무자동 승격).
.NOTES
  산출: reports/promotion_parallel_push_v1_latest.json
  NEVER: promote_op28_headline, apply Track A active, live enable
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipHeavy,
    [switch]$SkipPremium
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
$started = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$jobs = @(
    @{ Name = "promotion_evidence"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/build_mkm_promotion_gate_evidence_bundle_v1.py; exit $LASTEXITCODE } },
    @{ Name = "prophecy_recommended_eval"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/run_prophecy_btrack_recommended_eval_chain_v1.py; exit $LASTEXITCODE } },
    @{ Name = "myeongni_promotion_gate"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/build_myeongni_promotion_go_nogo_v1.py; exit $LASTEXITCODE } },
    @{ Name = "myeongni_shadow_gate"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/report_independent_lens_shadow_gate.py; exit $LASTEXITCODE } },
    @{ Name = "sasang12_chain"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/run_sasang12_promotion_candidate_chain_v1.py; exit $LASTEXITCODE } },
    @{ Name = "sasang_readiness"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/build_sasang_commercialization_readiness_packet.py; exit $LASTEXITCODE } },
    @{ Name = "promotion_push_180d"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/run_btrack_promotion_push_v1.py; exit $LASTEXITCODE } },
    @{ Name = "anchor_panel_promo"; Script = { param($R, $Py); Set-Location $R; & $Py scripts/run_btrack_anchor_panel_promotion_parallel_v1.py; exit $LASTEXITCODE } }
)

if (-not $SkipPremium) {
    $jobs += @{
        Name = "premium_multilens_gate"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PremiumMultilensQueueRoutine_v1.ps1 -SkipPytest -SkipDrain
            exit $LASTEXITCODE
        }
    }
}

if (-not $SkipHeavy) {
    $jobs += @{
        Name = "hybrid_180d_promo"
        Script = { param($R, $Py); Set-Location $R; & $Py scripts/run_btrack_hybrid_180d_promotion_parallel_v1.py; exit $LASTEXITCODE }
    }
}

$results = [ordered]@{}
$failed = @()
foreach ($j in $jobs) {
    Write-Host "Start: $($j.Name)" -ForegroundColor Cyan
    $h = Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $py
    $null = Wait-Job $h
    $code = if ($h.ChildJobs.Count -gt 0) { $h.ChildJobs[0].JobStateInfo.Reason } else { $null }
    $exit = 0
    if ($h.State -eq "Failed") { $exit = 1; $failed += $j.Name }
    else {
        Receive-Job $h -ErrorAction SilentlyContinue | Out-Null
        if ($h.State -ne "Completed") { $exit = 1; $failed += $j.Name }
    }
    $results[$j.Name] = @{ exit = $exit; state = $h.State }
    if ($exit -eq 0) { Write-Host "OK: $($j.Name)" -ForegroundColor Green }
    else { Write-Host "FAIL: $($j.Name) state=$($h.State)" -ForegroundColor Red }
    Remove-Job $h -Force
}

Write-Host "==> post-wave (serial): sync + readiness" -ForegroundColor Cyan
$post = @()
& $py scripts/sync_op29b_prophecy_gates_headline_v1.py --skip-headline-promote 2>&1 | Out-Host
$post += [ordered]@{ name = "sync_op29b_gates"; exit = $LASTEXITCODE }
$alignHuman = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_align_panel_human_approval_v1_latest.json"
if (Test-Path -LiteralPath $alignHuman) {
    Write-Host "SKIP: strict_streak_tick (align-panel human approval — do not overwrite gates SSOT)" -ForegroundColor Yellow
    $post += [ordered]@{ name = "strict_streak_tick"; exit = 0; skipped = "align_panel_human_approval" }
} else {
    $alignStreak = Join-Path $WorkspaceRoot "reports\prophecy_promotion_strict_streak_align_panel_v1.json"
    $tickArgs = @("scripts/run_prophecy_strict_streak_tick_v1.py")
    if (Test-Path -LiteralPath $alignStreak) {
        $tickArgs += @(
            "--streak-history-json", "reports/prophecy_promotion_strict_streak_align_panel_v1.json",
            "--no-sync-push-best"
        )
    }
    & $py @tickArgs 2>&1 | Out-Host
    $post += [ordered]@{ name = "strict_streak_tick"; exit = $LASTEXITCODE }
}
$gatesRec = Join-Path $WorkspaceRoot "reports\prophecy_promotion_gates_recommended_chain_v1_latest.json"
& $py scripts/build_prophecy_promotion_readiness_report_v1.py --gates-json $gatesRec 2>&1 | Out-Host
$post += [ordered]@{ name = "prophecy_readiness_recommended"; exit = $LASTEXITCODE }
if (Test-Path (Join-Path $WorkspaceRoot "reports\prophecy_promotion_gates_v1_op29b_lane_latest.json")) {
    & $py scripts/build_prophecy_promotion_readiness_report_v1.py `
        --gates-json reports/prophecy_promotion_gates_v1_op29b_lane_latest.json `
        --output reports/prophecy_promotion_readiness_op29b_lane_v1_latest.json 2>&1 | Out-Host
    $post += [ordered]@{ name = "prophecy_readiness_op29b_lane"; exit = $LASTEXITCODE }
}

function Read-J([string]$p) {
    if (-not (Test-Path $p)) { return $null }
    return Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
}

$rollup = [ordered]@{
    schema = "promotion_parallel_push_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    started_at_utc = $started
    parallel_jobs = $results
    post_wave = $post
    failed_parallel = @($failed)
    track_wall = [ordered]@{
        headline_ssot_untouched = $true
        track_a_live_auto_merge = $false
        research_only = $true
    }
    snapshots = [ordered]@{}
}

$snapPaths = @{
    recommended_gates = "reports\prophecy_promotion_gates_recommended_chain_v1_latest.json"
    sasang_gate = "docs\final\artifacts\sasang12_promotion_candidate_gate_latest.json"
    myeongni_gate = "docs\final\artifacts\myeongni_promotion_gate_latest.json"
    premium_gate = "docs\final\artifacts\premium_multilens_queue_promotion_gate_v1_latest.json"
    promotion_push = "reports\btrack_promotion_push_v1_latest.json"
    readiness = "reports\prophecy_promotion_readiness_report_v1_latest.json"
    evidence = "docs\final\artifacts\mkm_promotion_gate_evidence_bundle_v1.json"
}
foreach ($k in $snapPaths.Keys) {
    $p = Join-Path $WorkspaceRoot $snapPaths[$k]
    $j = Read-J $p
    if ($null -eq $j) { continue }
    $snap = [ordered]@{ path = $snapPaths[$k] }
    if ($j.status) { $snap.status = $j.status }
    if ($j.decision) { $snap.decision = $j.decision }
    if ($null -ne $j.automation_ready) { $snap.automation_ready = $j.automation_ready }
    if ($null -ne $j.combined_all_passed) { $snap.combined_all_passed = $j.combined_all_passed }
    if ($null -ne $j.outcome_class) { $snap.outcome_class = $j.outcome_class }
    if ($j.gate_taxonomy.outcome_class) { $snap.outcome_class = $j.gate_taxonomy.outcome_class }
    if ($null -ne $j.strict_pass_streak) { $snap.strict_pass_streak = $j.strict_pass_streak }
    if ($null -ne $j.auto_promote_ready) { $snap.auto_promote_ready = $j.auto_promote_ready }
    $rollup.snapshots[$k] = $snap
}

$outPath = Join-Path $WorkspaceRoot "reports\promotion_parallel_push_v1_latest.json"
$rollup | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "WROTE: $outPath failed=$($failed.Count)" -ForegroundColor Cyan

if ($failed.Count -gt 0) { exit 1 }
if (($post | Where-Object { $_.exit -ne 0 }).Count -gt 0) { exit 2 }
exit 0
