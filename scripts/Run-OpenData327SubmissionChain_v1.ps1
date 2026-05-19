#Requires -Version 5.1
<#
.SYNOPSIS
  OpenData 327 — alias for Run-OpenData327SubmissionPrep_v1.ps1 (gates + export + merge + readiness).
#>
$ErrorActionPreference = "Stop"
$prep = Join-Path (Split-Path -Parent $PSScriptRoot) "scripts\Run-OpenData327SubmissionPrep_v1.ps1"
& $prep @args
exit $LASTEXITCODE
