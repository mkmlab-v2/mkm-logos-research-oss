#Requires -Version 5.1
<#
.SYNOPSIS
  personadiary 오픈베타 원클릭: 토큰 프로브 → (가능 시) preview DNS → 빌드·배포.

.EXAMPLE
  powershell -File scripts\Invoke-PersonadiaryOpenBetaAutomation_v1.ps1 -Deploy

.EXAMPLE
  powershell -File scripts\Invoke-PersonadiaryOpenBetaAutomation_v1.ps1 -Deploy -WaitlistEmbedUrl "https://tally.so/embed/xxxx"
#>
param(
    [switch]$Deploy,
    [switch]$SkipDns,
    [string]$WaitlistEmbedUrl = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$bundleArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Invoke-PersonadiaryParallelBundle_v1.ps1")
if ($Deploy) { $bundleArgs += "-Deploy" }
if ($SkipDns) { $bundleArgs += "-SkipPreviewDns" }
else { $bundleArgs += "-DnsApply" }
if ($WaitlistEmbedUrl) { $bundleArgs += @("-WaitlistEmbedUrl", $WaitlistEmbedUrl) }

& powershell.exe @bundleArgs
$code = $LASTEXITCODE

if ($code -ne 0) {
    Write-Host ""
    Write-Host "자동화가 막힌 항목은 reports\personadiary_automation_blockers_latest.json 참고." -ForegroundColor Yellow
    if (Test-Path -LiteralPath (Join-Path $root "reports\personadiary_automation_blockers_latest.json")) {
        Get-Content -LiteralPath (Join-Path $root "reports\personadiary_automation_blockers_latest.json") -Raw | Write-Host
    }
}
exit $code
