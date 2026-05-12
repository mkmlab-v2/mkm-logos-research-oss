[CmdletBinding()]
param(
    [switch]$StrictMode,
    [switch]$RestoreAfterRun
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$art = Join-Path $repoRoot "docs\final\artifacts"
$recommendedPath = Join-Path $art "lens_music_prompt_poc_threshold_recommended_latest.json"
$statePath = Join-Path $art "lens_music_prompt_poc_threshold_recommendation_drift_state_latest.json"
$dispatchPath = Join-Path $art "lens_music_prompt_poc_threshold_recommendation_drift_webhook_dispatch_latest.json"
$rehearsalOutPath = Join-Path $art "lens_music_prompt_poc_threshold_watch_rehearsal_latest.json"

if (-not (Test-Path -LiteralPath $recommendedPath)) {
    throw "recommended artifact missing: $recommendedPath"
}

$recommendedBackup = "$recommendedPath.bak"
$stateBackup = "$statePath.bak"

Copy-Item -LiteralPath $recommendedPath -Destination $recommendedBackup -Force
if (Test-Path -LiteralPath $statePath) {
    Copy-Item -LiteralPath $statePath -Destination $stateBackup -Force
}

try {
    Set-Location -LiteralPath $repoRoot

    # Step 1: initialize baseline state using current recommendation.
    py scripts/check_lens_music_prompt_poc_threshold_recommendation_drift_v1.py
    if ($LASTEXITCODE -ne 0) { throw "baseline drift check failed" }

    # Step 2: force large threshold shift to produce WATCH.
    py -c "import json, pathlib; p=pathlib.Path(r'$recommendedPath'); d=json.loads(p.read_text(encoding='utf-8-sig')); d.setdefault('policy_targets',{}); d['policy_targets'].update({'min_samples': 96, 'style_delta_rate_min': 0.95, 'overlay_style_match_rate_min': 0.10}); p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')"
    if ($LASTEXITCODE -ne 0) { throw "failed to mutate recommended artifact" }

    py scripts/check_lens_music_prompt_poc_threshold_recommendation_drift_v1.py
    if ($LASTEXITCODE -ne 0) { throw "watch drift check failed" }

    if ($StrictMode) {
        $env:ENABLE_WEBHOOK_STRICT_MODE = "true"
    }
    else {
        Remove-Item Env:ENABLE_WEBHOOK_STRICT_MODE -ErrorAction SilentlyContinue
    }

    py scripts/dispatch_lens_music_prompt_poc_threshold_drift_webhook_v1.py
    $dispatchCode = $LASTEXITCODE

    if (-not (Test-Path -LiteralPath $dispatchPath)) {
        throw "dispatch artifact missing: $dispatchPath"
    }
    $dispatchObj = Get-Content -LiteralPath $dispatchPath -Raw | ConvertFrom-Json
    $driftObj = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json

    Write-Host "[watch-rehearsal] drift_state=$($driftObj.state) drift_reason=$($driftObj.reason)"
    Write-Host "[watch-rehearsal] dispatch_status=$($dispatchObj.dispatch.status) dispatch_reason=$($dispatchObj.dispatch.reason)"
    Write-Host "[watch-rehearsal] strict_mode=$StrictMode dispatch_exit_code=$dispatchCode"

    $rehearsalOut = @{
        schema = "lens_music_prompt_poc_threshold_watch_rehearsal_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        strict_mode = [bool]$StrictMode
        restore_after_run = [bool]$RestoreAfterRun
        drift_state = $driftObj.state
        drift_reason = $driftObj.reason
        dispatch_status = $dispatchObj.dispatch.status
        dispatch_reason = $dispatchObj.dispatch.reason
        dispatch_exit_code = $dispatchCode
        advisory_only = $true
        track = "B"
    }
    $rehearsalOut | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $rehearsalOutPath -Encoding UTF8
    Write-Host "[watch-rehearsal] output_json=$rehearsalOutPath"

    if ($driftObj.state -ne "WATCH") {
        throw "expected WATCH drift state, got: $($driftObj.state)"
    }

    py scripts/mkm_append_governance_audit_log_v1.py --mission-id lens_music_threshold_watch_rehearsal --stage governance_drill --decision watch_rehearsal_pass --evidence-path docs/final/artifacts/lens_music_prompt_poc_threshold_watch_rehearsal_latest.json --actor Run-LensMusicPromptPocThresholdDriftWebhookWatchRehearsal_v1.ps1 --note "strict_mode=$StrictMode;dispatch_exit=$dispatchCode"
}
finally {
    if ($RestoreAfterRun) {
        if (Test-Path -LiteralPath $recommendedBackup) {
            Move-Item -LiteralPath $recommendedBackup -Destination $recommendedPath -Force
        }
        if (Test-Path -LiteralPath $stateBackup) {
            Move-Item -LiteralPath $stateBackup -Destination $statePath -Force
        }
        Write-Host "[watch-rehearsal] restored recommended/state artifacts from backups"
    }
}
