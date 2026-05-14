<#
.SYNOPSIS
  Copy SSOT files from the monorepo root into _pr_sasang_promotion (PR pack / mirror).

.DESCRIPTION
  Keeps CI tail pointer policy and related docs aligned without hand-editing the mirror.
  Fixed list (10 relative paths): CONSTITUTION, MULTI_LENS, dual-regime-integrity, AGENTS, CLAUDE,
  P0 tracker, CENTRAL_AGENT_MEMORY, mkm-automation-gate.mdc, this script, run_workspace_automation_health.ps1.
  Idempotent: overwrites same relative paths under the mirror root.

.PARAMETER WorkspaceRoot
  Monorepo root (default: parent of scripts/).

.PARAMETER MirrorRelativePath
  Directory under WorkspaceRoot (default: _pr_sasang_promotion).

.PARAMETER WhatIf
  List planned copies only.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter()][string] $WorkspaceRoot = "",
    [Parameter()][string] $MirrorRelativePath = "_pr_sasang_promotion"
)

$ErrorActionPreference = "Stop"
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
} else {
    $WorkspaceRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
}
$mirrorRoot = Join-Path $WorkspaceRoot $MirrorRelativePath
if (-not (Test-Path -LiteralPath $mirrorRoot -PathType Container)) {
    Write-Error "Mirror not found: $mirrorRoot"
}

$relPaths = @(
    "AGENTS.md",
    "CLAUDE.md",
    "docs\final\CENTRAL_AGENT_MEMORY_V1.md",
    "docs\final\CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "docs\final\MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md",
    "docs\final\P0_COMMERCIALIZATION_TRACKER.md",
    ".github\workflows\dual-regime-integrity.yml",
    ".cursor\rules\mkm-automation-gate.mdc",
    "scripts\Sync-PrSasangPromotionMirror_v1.ps1",
    "scripts\run_workspace_automation_health.ps1"
)

$copied = 0
$skipped = 0
foreach ($rel in $relPaths) {
    $src = Join-Path $WorkspaceRoot $rel
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
        Write-Warning "Skip (missing source): $src"
        $skipped++
        continue
    }
    $dest = Join-Path $mirrorRoot $rel
    $destDir = Split-Path -Parent $dest
    if (-not (Test-Path -LiteralPath $destDir -PathType Container)) {
        if ($PSCmdlet.ShouldProcess($destDir, "Create directory")) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
    }
    if ($PSCmdlet.ShouldProcess($dest, "Copy-Item from $src")) {
        Copy-Item -LiteralPath $src -Destination $dest -Force
        $copied++
    }
}

Write-Host "Sync-PrSasangPromotionMirror_v1: copied=$copied skipped_missing=$skipped mirror=$mirrorRoot"
