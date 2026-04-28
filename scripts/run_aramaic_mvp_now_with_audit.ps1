param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$AuditLogJsonl = "reports/ops/aramaic_mvp_run_audit_log.jsonl",
    [switch]$StrictReadiness,
    [switch]$NoWebhook
)

$ErrorActionPreference = "Stop"

$chainScript = Join-Path $WorkspaceRoot "scripts\run_aramaic_mvp_chain_v1.ps1"
if (-not (Test-Path -LiteralPath $chainScript)) {
    throw "Missing chain script: $chainScript"
}

$auditPath = $AuditLogJsonl
if (-not [System.IO.Path]::IsPathRooted($auditPath)) {
    $auditPath = Join-Path $WorkspaceRoot $auditPath
}
$auditDir = Split-Path -Parent $auditPath
if (-not (Test-Path -LiteralPath $auditDir)) {
    New-Item -ItemType Directory -Path $auditDir -Force | Out-Null
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $chainScript
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$scorePath = Join-Path $WorkspaceRoot "docs\final\artifacts\aramaic_regime_shift_score_latest.json"
$shadowPath = Join-Path $WorkspaceRoot "docs\final\artifacts\aramaic_regime_shift_shadow_compare_latest.json"
if (-not (Test-Path -LiteralPath $scorePath)) { throw "Missing score artifact: $scorePath" }

$score = Get-Content -LiteralPath $scorePath -Encoding UTF8 | ConvertFrom-Json
$delta = 0.0
if (Test-Path -LiteralPath $shadowPath) {
    $shadow = Get-Content -LiteralPath $shadowPath -Encoding UTF8 | ConvertFrom-Json
    if ($null -ne $shadow.delta_shift_score) {
        $delta = [double]$shadow.delta_shift_score
    } elseif ($null -ne $shadow.delta -and $null -ne $shadow.delta.shift_score) {
        $delta = [double]$shadow.delta.shift_score
    }
}

$row = [ordered]@{
    run_at_utc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    shift_score = [double]$score.shift_score
    delta_shift_score = [double]$delta
    strict_readiness = [bool]$StrictReadiness
    webhook_disabled = [bool]$NoWebhook
}

$json = ($row | ConvertTo-Json -Compress -Depth 6)
[System.IO.File]::AppendAllText($auditPath, $json + [Environment]::NewLine, [System.Text.Encoding]::UTF8)

Write-Host ("AUDIT APPEND: {0}" -f $auditPath) -ForegroundColor Green
Write-Host ("AUDIT ROW: shift_score={0}, delta_shift_score={1}" -f $row.shift_score, $row.delta_shift_score) -ForegroundColor Green
