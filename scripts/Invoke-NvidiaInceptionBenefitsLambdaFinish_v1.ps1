#Requires -Version 5.1
<#
.SYNOPSIS
  CDP Chrome 탭 정리 후 Lambda $7,500 폼 마무리 (전화번호는 MKM_INCEPTION_CONTACT_PHONE 또는 form_answers).
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$cdp = 'http://127.0.0.1:9222'
$lambdaUrl = 'https://lambda.ai/nvidia-inception?benefit-activity-id=aG9Vv000000c4DtKAI'

& "$root\scripts\Start-ChromeForNvidiaInceptionCdp_v1.ps1" | Out-Null
py scripts/nvidia_inception_benefits_cdp_cleanup_v1.py --cdp-url $cdp --keep-url-contains 'lambda.ai'

# PowerShell $7 escape: 반드시 단일 인용부호
py scripts/nvidia_inception_benefits_catalog_request_v1.py `
    --cdp-url $cdp `
    --wait-for-login-sec 60 `
    --targets '$7,500 in Lambda Cloud Credits'

exit $LASTEXITCODE
