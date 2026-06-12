# Design/Showroom lane — hub·no1kmedi UI gates (no VPS deploy).
# SSOT: AGENTS.md 「Design 레인 자동 진입」·.cursor/rules/design-lane.mdc
param(
    [switch]$SkipHubShell,
    [switch]$SkipUiShellContract,
    [switch]$SkipNo1kmediCopy,
    [switch]$SkipDesignTokens
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$WorkspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

Push-Location $WorkspaceRoot
try {
    if (-not $SkipHubShell) {
        & py scripts/check_mkm_universe_hub_shell_v2.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if (-not $SkipUiShellContract) {
        & py scripts/check_mkm_ui_shell_contract_v1.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    $no1k = Join-Path $WorkspaceRoot 'projects/no1kmedi'
    if (-not (Test-Path -LiteralPath $no1k)) {
        Write-Warning "Skip no1kmedi npm gates — path missing: $no1k"
        exit 0
    }

    Push-Location $no1k
    try {
        if (-not $SkipNo1kmediCopy) {
            & npm run check:marketing-copy
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
        if (-not $SkipDesignTokens) {
            & npm run check:design-tokens
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
    }
    finally {
        Pop-Location
    }

    Write-Host '[DesignLane] hub shell + ui shell contract + marketing-copy + design-tokens OK'
    exit 0
}
finally {
    Pop-Location
}
