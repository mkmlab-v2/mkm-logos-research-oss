# Browser smoke artifact for ko shorts Cursor preview (Tier 2).
param([int]$Port = 8796)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $existing) {
    Start-Process -FilePath 'py' -ArgumentList @('-m', 'http.server', "$Port", '--bind', '127.0.0.1', '--directory', 'reports') `
        -WorkingDirectory $Root -WindowStyle Minimized | Out-Null
    Start-Sleep -Seconds 1
}

$previewUrl = "http://127.0.0.1:$Port/ko_shorts_cursor_preview_v1.html"
$artifact = Join-Path $Root 'reports/ko_shorts_cursor_browser_smoke_v1_latest.json'
$doc = @{
    schema = 'ko_shorts_cursor_browser_smoke_v1'
    research_only = $true
    send_gate = 'HOLD'
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    preview_url = $previewUrl
    agent_flow = @('browser_navigate', 'browser_lock', 'browser_snapshot', 'browser_unlock')
    reproduce = 'powershell -File scripts/Invoke-KoShortsCursorBrowserSmoke_v1.ps1'
} | ConvertTo-Json -Depth 4
Set-Content -LiteralPath $artifact -Value $doc -Encoding UTF8
Write-Host $previewUrl
exit 0
