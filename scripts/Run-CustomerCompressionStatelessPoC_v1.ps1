#Requires -Version 5.1
<#
.SYNOPSIS
  Customer JSONL -> V2 stateless_packet + codebook_only PoC report.
.EXAMPLE
  pwsh -File scripts/Run-CustomerCompressionStatelessPoC_v1.ps1 -InputJsonl data/track_a_shadow/conversations_sample_v1.jsonl
#>
param(
    [string]$WorkspaceRoot = "",
    [Parameter(Mandatory = $true)]
    [string]$InputJsonl,
    [int]$MaxCases = 200,
    [string]$LossProfile = "semantic_general"
)
$ErrorActionPreference = "Stop"
if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$inPath = if ([System.IO.Path]::IsPathRooted($InputJsonl)) { $InputJsonl } else { Join-Path $WorkspaceRoot $InputJsonl }
& py (Join-Path $WorkspaceRoot "scripts/run_customer_compression_stateless_poc_v1.py") `
    --workspace-root $WorkspaceRoot `
    --input-jsonl $inPath `
    --max-cases $MaxCases `
    --loss-profile $LossProfile
exit $LASTEXITCODE
