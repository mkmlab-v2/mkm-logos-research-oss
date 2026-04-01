param(
    [Parameter(Mandatory = $true)]
    [string]$TargetPath,
    [string]$Label = "scheduled task target"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $TargetPath)) {
    throw "$Label not found: $TargetPath"
}
