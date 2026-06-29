param(
    [string]$ShareRoot = "Z:\external_validation_d6_aux",
    [string]$AuxWorkspace = "C:\workspace",
    [switch]$CollectOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

if (-not $CollectOnly) {
    Write-Host "[1/2] stage aux drop on $ShareRoot" -ForegroundColor Cyan
    py scripts/stage_external_validation_d6_aux_drop_v1.py --share-root $ShareRoot --aux-workspace $AuxWorkspace
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host ""
    Write-Host "On AUX PC: open share folder and run RUN_D6_ON_AUX.cmd (or CURSOR_PROMPT.txt in VS Code)" -ForegroundColor Yellow
    Write-Host "Then on MAIN: powershell -File scripts\Invoke-ExternalValidationD6Aux_v1.ps1 -CollectOnly" -ForegroundColor Yellow
    exit 0
}

Write-Host "[collect] aux D6 result from $ShareRoot" -ForegroundColor Cyan
py scripts/collect_external_validation_d6_aux_result_v1.py --share-root $ShareRoot
exit $LASTEXITCODE
