#Requires -Version 5.1
<#
.SYNOPSIS
  Free auditable cinematic proof bundle — economy + hybrid donor reuse ($0 API).

.DESCRIPTION
  Runs economy (scenario-aligned animatic) and hybrid (reuse local Veo donor pack),
  then writes injection manifest + hero rubric check. No Vertex spend.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Bundle = Join-Path $Root "scripts\cinematic\run_auditable_cinematic_free_bundle_v1.py"

Push-Location $Root
try {
    & py $Bundle @args
    if ($LASTEXITCODE -ne 0) { throw "bundle exit $LASTEXITCODE" }
    exit 0
}
finally {
    Pop-Location
}
