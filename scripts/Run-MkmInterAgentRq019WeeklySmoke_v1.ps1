<#
.SYNOPSIS
  Weekly smoke: RQ-019 inter-agent wire lane (quick regression, no live HTTP re-capture).

.DESCRIPTION
  Runs: py scripts/run_mkm_inter_agent_rq019_regression_chain_v1.py --skip-pytest
  Optional: py scripts/build_mkm_inter_agent_encoding_status_v1.py --skip-pytest

.PARAMETER SkipEncodingStatus
  Skip encoding status refresh after regression.

.PARAMETER WorkspaceRoot
  Repo root (default: MKM_WORKSPACE_ROOT or parent of scripts/).
#>
param(
    [switch]$SkipEncodingStatus,
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Push-Location $resolvedRoot
try {
    & $py scripts/run_mkm_inter_agent_rq019_regression_chain_v1.py --skip-pytest
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not $SkipEncodingStatus) {
        & $py scripts/build_mkm_inter_agent_encoding_status_v1.py --skip-pytest
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host "OK: RQ-019 weekly smoke (quick regression)"
    exit 0
}
finally {
    Pop-Location
}
