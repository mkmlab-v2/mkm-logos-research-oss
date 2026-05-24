# Deprecated wrapper — SSOT: Invoke-MyeongriInterpretPivotA_v1.ps1 (Pack0-B pivot A-path).
param(
    [int]$TemplateLimit = 25,
    [int]$TrainSteps = 100,
    [switch]$SkipTrain,
    [switch]$SkipTemplate
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    if (-not $SkipTemplate) {
        & py scripts/run_myeongri_interpret_template_only_chain_v1.py --limit $TemplateLimit
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    $pivotArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $root "scripts\Invoke-MyeongriInterpretPivotA_v1.ps1"),
        "-TrainSteps", $TrainSteps,
        "-EvalLimit", $TemplateLimit
    )
    if ($SkipTrain) { $pivotArgs += "-SkipTrain" }
    Write-Host "Forwarding to pivot A-path SSOT: Invoke-MyeongriInterpretPivotA_v1.ps1"
    & powershell @pivotArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
