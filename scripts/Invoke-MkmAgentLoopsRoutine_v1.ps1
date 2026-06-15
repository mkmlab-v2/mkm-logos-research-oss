#Requires -Version 5.1
<#
.SYNOPSIS
  MKM agent micro-loops SSOT routine — artifact presence + P0 + context diet.

.DESCRIPTION
  Kickoff catalog: docs/final/artifacts/mkm_agent_loops_v1_latest.md
  NOT a chat loop runner — validates SSOT and baseline gates only.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmAgentLoopsRoutine_v1.ps1
#>
param(
    [switch]$SkipP0,
    [switch]$SkipContextDiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$WorkspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$artifactRel = 'docs\final\artifacts\mkm_agent_loops_v1_latest.md'
$artifact = Join-Path $WorkspaceRoot $artifactRel
$reportRel = 'reports\mkm_agent_loops_routine_v1_latest.json'
$report = Join-Path $WorkspaceRoot $reportRel

Push-Location $WorkspaceRoot
try {
    if (-not (Test-Path -LiteralPath $artifact)) {
        Write-Error "Missing SSOT: $artifactRel"
    }

    $md = Get-Content -LiteralPath $artifact -Raw -Encoding UTF8
    $requiredHeadings = @(
        '## 1. P0 Until Green',
        '## 2. Bounded Lane Shadow Until Pass',
        '## 3. Parallel Passive Until OK',
        '## 4. CI Failure Watcher',
        '## 5. De-Sloppify Pass'
    )
    $missing = @($requiredHeadings | Where-Object { $md -notmatch [regex]::Escape($_) })
    if ($missing.Count -gt 0) {
        Write-Error ("SSOT missing sections: " + ($missing -join '; '))
    }

    $p0Exit = 0
    if (-not $SkipP0) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'verify_p0_constitution_gate_paths.ps1') -WorkspaceRoot $WorkspaceRoot
        $p0Exit = $LASTEXITCODE
        if ($p0Exit -ne 0) { exit $p0Exit }
    }

    $dietExit = 0
    if (-not $SkipContextDiet) {
        & py scripts/check_cursor_rules_context_diet_v1.py --strict
        $dietExit = $LASTEXITCODE
        if ($dietExit -ne 0) { exit $dietExit }
    }

    $payload = @{
        schema          = 'mkm_agent_loops_routine_v1'
        ok              = $true
        artifact_path   = $artifactRel.Replace('\', '/')
        loop_count      = 5
        p0_skipped      = [bool]$SkipP0
        context_diet_skipped = [bool]$SkipContextDiet
        p0_exit         = $p0Exit
        context_diet_exit = $dietExit
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    } | ConvertTo-Json -Depth 4

    $reportDir = Split-Path -Parent $report
    if (-not (Test-Path -LiteralPath $reportDir)) {
        New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
    }
    Set-Content -LiteralPath $report -Value $payload -Encoding UTF8

    Write-Host "[MkmAgentLoops] SSOT OK · loops=5 · report=$reportRel"
    exit 0
}
finally {
    Pop-Location
}
