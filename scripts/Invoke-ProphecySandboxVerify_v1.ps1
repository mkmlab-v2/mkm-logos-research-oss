#Requires -Version 5.1
<#
.SYNOPSIS
  Prophecy Sandbox verify bundle: scheduled tasks + artifact presence gate.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipScheduledTasks,
    [switch]$SkipArtifacts
)

$ErrorActionPreference = "Stop"
Push-Location $WorkspaceRoot
try {
    if (-not $SkipScheduledTasks) {
        $verifyTasks = Join-Path $PSScriptRoot "Verify-ProphecySandboxScheduledTasks_v1.ps1"
        if (-not (Test-Path -LiteralPath $verifyTasks)) { throw "Missing: $verifyTasks" }
        & powershell -NoProfile -ExecutionPolicy Bypass -File $verifyTasks `
            -WorkspaceRoot $WorkspaceRoot `
            -OutJson "reports\sandbox_prophecy_scheduled_tasks_verify_v1_latest.json"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if (-not $SkipArtifacts) {
        & py scripts/verify_sandbox_prophecy_artifacts_v1.py
        exit $LASTEXITCODE
    }
    exit 0
}
finally {
    Pop-Location
}
