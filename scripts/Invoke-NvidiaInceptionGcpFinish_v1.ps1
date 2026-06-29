#Requires -Version 5.1
<#
.SYNOPSIS
  Google 로그인 완료 후 GCP startup apply 폼 마무리.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& "$root\scripts\Start-ChromeForNvidiaInceptionCdp_v1.ps1" | Out-Null
py scripts/nvidia_inception_gcp_probe_v1.py
exit $LASTEXITCODE
