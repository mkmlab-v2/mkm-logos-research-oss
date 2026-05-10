#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot NotebookLM MCP hygiene probe for automation / 암행어사-style watchdogs.

.DESCRIPTION
  Runs check_notebooklm_mcp_prereqs.ps1 (always), optionally repair_notebooklm_mcp_auth_stuck.ps1,
  emits a small JSON summary to stdout and optionally to -OutJson.

  Does NOT call MCP get_health (authenticated flag requires Cursor-injected MCP).

.PARAMETER Repair
  Run repair_notebooklm_mcp_auth_stuck.ps1 after prereq (kills stale chrome/node per script rules).

.PARAMETER StrictPrereq
  Forward -Strict to prereq (warnings -> exit 1).

.PARAMETER OutJson
  Write the same JSON object to this path (UTF-8).

.PARAMETER Quiet
  Suppress human-readable lines; JSON only on stdout at end (still prints prereq/repair output unless we tee - for Quiet use $null redirects)

.NOTES
  Exit codes: same as prereq when -Repair omitted (0/1/2). With -Repair: 2 if prereq errors,
  else repair exit if non-zero, else prereq exit.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Repair,
    [switch]$StrictPrereq,
    [int]$StaleNodeMaxHours = 12,
    [string]$OutJson = "",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Get-StaleNotebookLmProcessCount {
    param([int]$Hours)
    $cutoff = (Get-Date).AddHours(-1 * $Hours)
    return @(
        Get-CimInstance Win32_Process | Where-Object {
            $_.CommandLine -like '*notebooklm-mcp*' -and
            ($_.Name -in @('node.exe', 'cmd.exe')) -and
            ($_.CreationDate -lt $cutoff)
        }
    ).Count
}

$prereqScript = Join-Path $WorkspaceRoot "scripts\check_notebooklm_mcp_prereqs.ps1"
$repairScript = Join-Path $WorkspaceRoot "scripts\repair_notebooklm_mcp_auth_stuck.ps1"

if (-not (Test-Path -LiteralPath $prereqScript)) {
    throw "Missing $prereqScript"
}

if (-not $Quiet) {
    Write-Host "=== MCP hygiene probe (NotebookLM) ===" -ForegroundColor Cyan
    Write-Host "WorkspaceRoot: $WorkspaceRoot"
}

$prereqArgs = @{
    WorkspaceRoot       = $WorkspaceRoot
    StaleNodeMaxHours   = $StaleNodeMaxHours
    Strict              = $StrictPrereq
}
if ($Quiet) {
    # note: prereq uses Write-Host; full silence requires wrapping the whole probe in *> $null
    $null = & $prereqScript @prereqArgs 2>&1
} else {
    & $prereqScript @prereqArgs
}
$prereqExit = $LASTEXITCODE
if ($null -eq $prereqExit) { $prereqExit = 0 }

$staleBefore = Get-StaleNotebookLmProcessCount -Hours $StaleNodeMaxHours

$repairRan = $false
$repairExit = $null
if ($Repair) {
    if (-not (Test-Path -LiteralPath $repairScript)) {
        throw "Missing $repairScript"
    }
    $repairRan = $true
    if (-not $Quiet) {
        Write-Host "`n--- repair ---" -ForegroundColor Yellow
    }
    if ($Quiet) {
        $null = & $repairScript -StaleNodeMaxHours $StaleNodeMaxHours 2>&1
    } else {
        & $repairScript -StaleNodeMaxHours $StaleNodeMaxHours
    }
    $repairExit = $LASTEXITCODE
    if ($null -eq $repairExit) { $repairExit = 0 }
}

$staleAfter = Get-StaleNotebookLmProcessCount -Hours $StaleNodeMaxHours

$payload = [ordered]@{
    schema               = "mcp_hygiene_probe_notebooklm_v1"
    generated_at_utc     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    workspace_root       = $WorkspaceRoot
    prereq_script        = $prereqScript
    prereq_exit_code     = $prereqExit
    prereq_strict        = [bool]$StrictPrereq
    stale_process_count_before = $staleBefore
    repair_ran           = $repairRan
    repair_exit_code     = $repairExit
    stale_process_count_after  = $staleAfter
    cursor_mcp_note      = "get_health.authenticated requires MCP tools inside Cursor; not probed here."
    ssot                 = "docs/NotebookLM_sources_manifest.md"
}

$json = $payload | ConvertTo-Json -Depth 5 -Compress

if (-not $Quiet) {
    Write-Host "`n--- JSON ---" -ForegroundColor DarkGray
}
Write-Output $json

if ($OutJson) {
    $dir = Split-Path -Parent $OutJson
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Set-Content -LiteralPath $OutJson -Value $json -Encoding UTF8
    if (-not $Quiet) {
        Write-Host "Wrote: $OutJson" -ForegroundColor Green
    }
}

# Exit policy
if ($prereqExit -eq 2) { exit 2 }
if ($repairRan -and $repairExit -ne 0) { exit [int]$repairExit }
if ($prereqExit -ne 0) { exit $prereqExit }
exit 0
