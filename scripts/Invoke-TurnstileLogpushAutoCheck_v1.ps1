#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot Turnstile Logpush status (API only, no CF login).

  py scripts/check_turnstile_logpush_auto_v1.py
#>
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"
& py scripts/check_turnstile_logpush_auto_v1.py
exit $LASTEXITCODE
