param(
    [string]$To = "admin@no1kmedi.com",
    [string]$Subject = "[Action Required] Macro Risk Warning API 파일럿 Base URL 확정 요청",
    [string]$BodyFile = "docs/final/artifacts/macro_risk_warning_api_base_url_confirmation_email_live_v1.md"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$bodyPath = if ([System.IO.Path]::IsPathRooted($BodyFile)) { $BodyFile } else { Join-Path $repoRoot $BodyFile }

if (-not (Test-Path -LiteralPath $bodyPath)) {
    throw "Body file not found: $bodyPath"
}

$body = Get-Content -LiteralPath $bodyPath -Raw -Encoding UTF8

$outlook = New-Object -ComObject Outlook.Application
$mail = $outlook.CreateItem(0)
$mail.To = $To
$mail.Subject = $Subject
$mail.Body = $body
$mail.Send()

Write-Host "outlook_local_send: PASS"
Write-Host "to=$To"
Write-Host "subject=$Subject"
