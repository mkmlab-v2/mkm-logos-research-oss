<#
.SYNOPSIS
  Weekly Hub B prep: run NotebookLM → vault mirror (SSOT paths) and append one JSONL audit line.

.DESCRIPTION
  Fact-Lock: mirrors files per docs/NotebookLM_sources_manifest.md via sync_notebooklm_sources_to_mkm_data_vault.ps1.
  Cloud NotebookLM "Hub B" ingest (source_add) remains a separate step — MCP or UI — after the vault copy exists.

.PARAMETER WhatIf
  Passes through to vault sync; still writes a log line with step what_if.

.PARAMETER Strict
  Passes through to vault sync (fail if any listed source missing).

.PARAMETER SkipVaultSync
  Only append log line (e.g. dry documentation); does not call sync.

.NOTES
  Log: reports/hub_b_weekly_mirror_log.jsonl (one compact JSON object per run).
#>
param(
    [switch]$WhatIf,
    [switch]$Strict,
    [switch]$SkipVaultSync
)

$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$reportsDir = Join-Path $workspaceRoot "reports"
$logPath = Join-Path $reportsDir "hub_b_weekly_mirror_log.jsonl"
$syncScript = Join-Path $PSScriptRoot "sync_notebooklm_sources_to_mkm_data_vault.ps1"

if (-not (Test-Path -LiteralPath $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

$exitCode = 0
$step = "vault_mirror"
$skipReason = $null
$errMsg = $null

if ($SkipVaultSync) {
    $step = "skipped"
    $skipReason = "SkipVaultSync: no vault sync executed"
} else {
    if (-not (Test-Path -LiteralPath $syncScript)) {
        throw "Sync script not found: $syncScript"
    }
    # Run sync in a child process so its `exit` does not terminate this script's session.
    $syncArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $syncScript,
        "-WorkspaceRoot", $workspaceRoot
    )
    if ($WhatIf) { $syncArgs += "-WhatIf" }
    if ($Strict) { $syncArgs += "-Strict" }
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $syncArgs -Wait -PassThru -NoNewWindow
    $exitCode = $proc.ExitCode
    if ($null -eq $exitCode) { $exitCode = 1 }
}

$ts = (Get-Date).ToUniversalTime().ToString("o")
$record = [ordered]@{
    schema      = "hub_b_weekly_mirror_v1"
    ts_utc      = $ts
    exit_code   = $exitCode
    step        = $step
    workspace   = $workspaceRoot
    sync_script = "scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1"
    whatif      = [bool]$WhatIf
    strict      = [bool]$Strict
    note        = "Hub B cloud ingest is separate: NotebookLM source_add or UI after vault mirror; see docs/NotebookLM_sources_manifest.md (Finance Hub B)."
}
if ($skipReason) { $record["skip_reason"] = $skipReason }
if ($errMsg) { $record["error"] = $errMsg }

$line = ($record | ConvertTo-Json -Compress -Depth 6)
Add-Content -LiteralPath $logPath -Value $line -Encoding utf8

Write-Host "[HubB weekly mirror] exit_code=$exitCode log=$logPath step=$step" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Red" })
exit $exitCode
