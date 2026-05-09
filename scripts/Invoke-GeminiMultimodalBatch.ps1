<#
.SYNOPSIS
  gemini_multimodal_batch.py 래퍼 (Windows). 동일 인자 전달.

.EXAMPLE
  .\Invoke-GeminiMultimodalBatch.ps1 research -f .\paper.pdf -p "핵심만 요약" --google-search

.EXAMPLE
  .\Invoke-GeminiMultimodalBatch.ps1 image -p "flat vector mascot" -o .\out\generated

.EXAMPLE
  .\Invoke-GeminiMultimodalBatch.ps1 crosscheck -f .\chart.png -m "BTC 4h"
#>
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('research', 'image', 'crosscheck', 'check')]
    [string]$Command,

    [ValidateSet('none', 'low-cost', 'normal')]
    [string]$BudgetProfile = 'normal',

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'
$py = Join-Path $PSScriptRoot 'gemini_multimodal_batch.py'
if (-not (Test-Path $py)) { throw "Not found: $py" }

if ($BudgetProfile -ne 'none') {
    switch ($BudgetProfile) {
        'low-cost' {
            $env:GEMINI_BATCH_DAILY_MAX_CALLS = '8'
            $env:GEMINI_BATCH_MONTHLY_MAX_CALLS = '120'
        }
        'normal' {
            $env:GEMINI_BATCH_DAILY_MAX_CALLS = '25'
            $env:GEMINI_BATCH_MONTHLY_MAX_CALLS = '400'
        }
    }
}

Write-Host "[gemini-batch] command=$Command budget_profile=$BudgetProfile"
if ($BudgetProfile -ne 'none') {
    Write-Host "[gemini-batch] caps: daily=$env:GEMINI_BATCH_DAILY_MAX_CALLS monthly=$env:GEMINI_BATCH_MONTHLY_MAX_CALLS"
}

if ($BudgetProfile -eq 'low-cost') {
    $argText = ($Args -join ' ')
    if ($argText -match '(^|\s)--google-search(\s|$)' -or $argText -match '(^|\s)--code-execution(\s|$)') {
        throw "low-cost 프로파일에서는 --google-search/--code-execution 사용이 차단됩니다. normal 프로파일 또는 -BudgetProfile none을 사용하세요."
    }
}

& py $py $Command @Args
