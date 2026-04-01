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

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'
$py = Join-Path $PSScriptRoot 'gemini_multimodal_batch.py'
if (-not (Test-Path $py)) { throw "Not found: $py" }

& py $py $Command @Args
