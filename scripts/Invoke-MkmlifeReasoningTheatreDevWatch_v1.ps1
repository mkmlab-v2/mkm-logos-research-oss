#requires -Version 5.1
<#
.SYNOPSIS
  Start mkmlife dev (if :3105 free) + Reasoning Theatre file-watch smoke loop.
.EXAMPLE
  powershell -File scripts/Invoke-MkmlifeReasoningTheatreDevWatch_v1.ps1
#>
param(
  [string]$BaseUrl = $(if ($env:MKMLIFE_DEV_URL) { $env:MKMLIFE_DEV_URL } else { 'http://127.0.0.1:3105' }),
  [int]$Port = 3105
)

$ErrorActionPreference = 'Stop'
$root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$mkmlife = Join-Path $root 'projects\mkm\mkm-life'

function Test-PortListening([int]$p) {
  return $null -ne (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

$devJob = $null
if (-not (Test-PortListening -p $Port)) {
  Write-Host "[theatre-dev-watch] starting npm run dev on :$Port"
  $devJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    npm run dev 2>&1
  } -ArgumentList $mkmlife
  Start-Sleep -Seconds 3
} else {
  Write-Host "[theatre-dev-watch] :$Port already listening — reusing dev"
}

$env:MKMLIFE_DEV_URL = $BaseUrl
Push-Location $mkmlife
try {
  $exit = 0
  node ./scripts/watch-reasoning-theatre-dev.mjs $BaseUrl
  if ($null -ne $LASTEXITCODE) { $exit = $LASTEXITCODE }
} finally {
  Pop-Location
  if ($devJob) {
    Stop-Job $devJob -ErrorAction SilentlyContinue
    Remove-Job $devJob -Force -ErrorAction SilentlyContinue
  }
}
exit $exit
