#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot web_ops_regime full bundle: CDP probe → baseline seed → gate check.

.EXAMPLE
  pwsh -File scripts/Run-WebOpsRegimeFullBundle_v1.ps1

.EXAMPLE
  pwsh -File scripts/Run-WebOpsRegimeFullBundle_v1.ps1 -SkipLiveCdp -RequireDualAlignment
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
& py (Join-Path $root "scripts\run_web_ops_regime_full_bundle_v1.py") @args
exit $LASTEXITCODE
