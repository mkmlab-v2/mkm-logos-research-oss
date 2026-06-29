#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly MKM Test Recovery (Safe): P0 paths + automation_registry pytest smoke.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmTestRecoverySafe_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$steps = [ordered]@{}
$ok = $true

function Invoke-Step {
    param([string]$Name, [scriptblock]$Block)
    & $Block
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $steps[$Name] = @{ exit_code = $code }
    if ($code -ne 0) { $script:ok = $false }
}

Invoke-Step "p0_constitution_paths" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\verify_p0_constitution_gate_paths.ps1") -WorkspaceRoot $WorkspaceRoot
}

Invoke-Step "automation_registry_pytest" {
    py -m pytest (Join-Path $WorkspaceRoot "tests\test_automation_registry_json_v1.py") -q
}

$utcNow = (Get-Date).ToUniversalTime()
$report = [ordered]@{
    schema = "mkm_test_recovery_safe_v1"
    generated_at_utc = $utcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    workspace_root = $WorkspaceRoot
    ok = $ok
    steps = $steps
    note_ko = "Read-only recovery smoke: P0 paths + automation_registry contract pytest"
}

$outDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$outPath = Join-Path $outDir "mkm_test_recovery_safe_latest.json"
$jsonText = $report | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($outPath, $jsonText, [System.Text.UTF8Encoding]::new($false))

Write-Host "WROTE: $outPath"
Write-Host "TEST_RECOVERY_SAFE_OK=$ok"
if (-not $ok) { exit 1 }
exit 0
