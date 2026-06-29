#Requires -Version 5.1

<#

.SYNOPSIS

  RQ-031 operator-assist lane routine: promotion rq bundle + lane freeze + gate [HYPO].

#>

param(

    [string]$WorkspaceRoot = "C:\workspace",

    [string]$SessionDate = "",

    [switch]$SkipGovernorBundle,

    [switch]$Strict

)



$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $WorkspaceRoot



$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (-not $SessionDate) {

    $SessionDate = (Get-Date).ToString("yyyy-MM-dd")

}



$promoBundle = Join-Path $WorkspaceRoot "scripts\Run-ACodePromotionRqDiscussionBundle_v1.ps1"

Write-Host "[operator-lane] promotion rq discussion bundle" -ForegroundColor Cyan

$promoArgs = @("-WorkspaceRoot", $WorkspaceRoot, "-SessionDate", $SessionDate)

if ($SkipGovernorBundle) { $promoArgs += "-SkipGovernorBundle" }

if ($Strict) { $promoArgs += "-Strict" }

& pwsh -NoProfile -ExecutionPolicy Bypass -File $promoBundle @promoArgs

if ($LASTEXITCODE -ne 0) { throw "promotion rq bundle exit $LASTEXITCODE" }



Write-Host "[operator-lane] done (lane freeze + gate via rq031 bundle)" -ForegroundColor Green

