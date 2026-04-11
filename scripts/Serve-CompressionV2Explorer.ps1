param(
    [int]$Port = 8765,
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = Split-Path -Parent $PSScriptRoot
}
$dir = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp"
if (-not (Test-Path -LiteralPath $dir)) {
    throw "Explorer directory not found: $dir"
}
Set-Location $dir
Write-Host "Serving jemaai-cloud-mvp on http://127.0.0.1:$Port/" -ForegroundColor Cyan
Write-Host "  Explorer: http://127.0.0.1:$Port/compression_v2_explorer.html" -ForegroundColor Green
Write-Host "  Start V1 stub: uvicorn scripts.compression_token_api_stub:app --host 127.0.0.1 --port 8010 (repo root)" -ForegroundColor DarkGray
Write-Host "  Start V2 stub: uvicorn scripts.compression_token_api_v2_stub:app --host 127.0.0.1 --port 8011 (repo root)" -ForegroundColor DarkGray
py -m http.server $Port --bind 127.0.0.1
