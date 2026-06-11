#Requires -Version 5.1
<#
.SYNOPSIS
  Run a-codeai public + open-bench binding checks and refresh launch checklist JSON.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

& py (Join-Path $WorkspaceRoot "scripts\check_a_codeai_public_binding_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $WorkspaceRoot "scripts\check_a_codeai_open_bench_binding_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $WorkspaceRoot "scripts\build_a_codeai_public_benchmark_launch_checklist_v1.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] a-codeai binding routine complete" -ForegroundColor Green
