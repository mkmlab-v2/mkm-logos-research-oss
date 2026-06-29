#Requires -Version 5.1
<#
.SYNOPSIS
  Daily MKM Morning Beans chain: build feed JSON + mkmlife card export.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipMkmlifePublicCopy,
    [switch]$FailOnGuardrail
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$buildArgs = @("scripts/build_mkm_morning_beans_feed_v1.py")
if ($FailOnGuardrail) { $buildArgs += "--fail-on-guardrail" }

& py @buildArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$exportArgs = @("scripts/export_mkm_morning_beans_mkmlife_card_v1.py")
if (-not $SkipMkmlifePublicCopy) { $exportArgs += "--copy-mkmlife-public" }

& py @exportArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[morning-beans] chain OK"
exit 0
