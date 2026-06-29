#Requires -Version 5.1
<#
.SYNOPSIS
  Weekly MKM Doc Sync (Safe): P0 paths + compression narrative Fact-Lock lint.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmDocSyncSafe_v1.ps1
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

Invoke-Step "compression_narrative_fact_lock" {
    py (Join-Path $WorkspaceRoot "scripts\check_compression_narrative_fact_lock_v1.py")
}

$utcNow = (Get-Date).ToUniversalTime()
$report = [ordered]@{
    schema = "mkm_doc_sync_safe_v1"
    generated_at_utc = $utcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    workspace_root = $WorkspaceRoot
    ok = $ok
    steps = $steps
    note_ko = "Read-only doc sync smoke: P0 paths + compression narrative Fact-Lock lint"
}

$outDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$outPath = Join-Path $outDir "mkm_doc_sync_safe_latest.json"
$jsonText = $report | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($outPath, $jsonText, [System.Text.UTF8Encoding]::new($false))

Write-Host "WROTE: $outPath"
Write-Host "DOC_SYNC_SAFE_OK=$ok"
if (-not $ok) { exit 1 }
exit 0
