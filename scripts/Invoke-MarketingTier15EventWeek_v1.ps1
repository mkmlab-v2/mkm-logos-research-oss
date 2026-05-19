<#
.SYNOPSIS
  Enable tier_15 event-week on marketing_content_queue.json (one Gemini LinkedIn post).

.DESCRIPTION
  Does NOT set .env for you. After this, add MKM_MARKETING_GEMINI_ALLOWED=1 to .env then:
  Run-MarketingWeeklyDraftBundle_v1.ps1 -Gemini [-WithChart]

.PARAMETER GeminiItemId
  LinkedIn queue item id (default: compression_governance_moat_w12).

.PARAMETER RevertTier0
  Reset to tier_0 and clear event week flags.
#>
param(
    [string]$GeminiItemId = "compression_governance_moat_w12",
    [switch]$RevertTier0
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$setter = Join-Path $root "scripts\set_marketing_queue_cost_tier_v1.py"

if ($RevertTier0) {
    & py $setter --active-tier tier_0 --clear-event-week --reset-gemini-flags
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $envPath = Join-Path $root ".env"
    if (Test-Path -LiteralPath $envPath) {
        $lines = @(Get-Content -LiteralPath $envPath)
        $found = $false
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match '^\s*#?\s*MKM_MARKETING_GEMINI_ALLOWED\s*=') {
                $lines[$i] = 'MKM_MARKETING_GEMINI_ALLOWED=0'
                $found = $true
                break
            }
        }
        if (-not $found) { $lines += 'MKM_MARKETING_GEMINI_ALLOWED=0' }
        Set-Content -LiteralPath $envPath -Value $lines -Encoding UTF8
        Write-Host '[DONE] MKM_MARKETING_GEMINI_ALLOWED=0 in .env (event week off).' -ForegroundColor DarkGray
    }
    Write-Host "[DONE] Reverted to tier_0. Weekly task stays assemble-only." -ForegroundColor Green
    exit 0
}

& py $setter --active-tier tier_15 --event-week --gemini-item $GeminiItemId
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "tier_15 event week enabled for item: $GeminiItemId" -ForegroundColor Cyan
Write-Host "1) Add to .env:  MKM_MARKETING_GEMINI_ALLOWED=1" -ForegroundColor Yellow
Write-Host "2) Run once:     powershell -File scripts\Run-MarketingWeeklyDraftBundle_v1.ps1 -Gemini" -ForegroundColor Yellow
Write-Host "3) After publish: powershell -File scripts\Invoke-MarketingTier15EventWeek_v1.ps1 -RevertTier0" -ForegroundColor Yellow
exit 0
