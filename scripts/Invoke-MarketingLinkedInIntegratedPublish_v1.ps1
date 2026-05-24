<#
.SYNOPSIS
  One-shot: tier15 Gemini moat regen (optional) → Phase2 approve+prep → tier_0 revert → OpenChrome publish (agent).

.EXAMPLE
  powershell -File scripts/Invoke-MarketingLinkedInIntegratedPublish_v1.ps1
  powershell -File scripts/Invoke-MarketingLinkedInIntegratedPublish_v1.ps1 -SkipGeminiRegen
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipGeminiRegen,
    [switch]$NoChart
)

$ErrorActionPreference = "Stop"
$root = if ($WorkspaceRoot) { (Resolve-Path -LiteralPath $WorkspaceRoot).Path } else { Split-Path -Parent $PSScriptRoot }
$py = Join-Path $root "scripts\run_marketing_linkedin_integrated_v1.py"

$argsList = @($py, "--prep-pc", "--revert-tier0")
if (-not $SkipGeminiRegen) { $argsList += "--gemini-regen-moat" }
if ($NoChart) { $argsList += "--no-chart" }

& py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "[DONE] Integrated prep: reports/marketing/marketing_linkedin_integrated_latest.json" -ForegroundColor Green
Write-Host "[NEXT] Agent: OpenChrome headed publish moat then showroom; then:" -ForegroundColor Cyan
Write-Host '  py scripts/marketing_linkedin_publish_closure_v1.py --phrase "올렸어"' -ForegroundColor Yellow
exit 0
