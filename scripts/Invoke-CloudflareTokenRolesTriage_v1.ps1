#Requires -Version 5.1
<#
.SYNOPSIS
  CF token roles triage (mkmlife analytics vs jemaai rulesets) — recurrence guard SSOT.
.NOTES
  Exit 0 = jemaai rulesets automation ready. Exit 2 = scope mismatch (set RULESETS once). Exit 1 = missing/invalid.
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
& $py scripts/check_cloudflare_token_roles_v1.py
exit $LASTEXITCODE
