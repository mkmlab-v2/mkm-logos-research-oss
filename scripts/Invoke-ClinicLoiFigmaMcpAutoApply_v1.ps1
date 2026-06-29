# Enable Figma MCP then auto-apply clinic LOI tokens via use_figma (next chat turn).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$figmaUrl = "https://www.figma.com/design/8Ey3MEkXhH8EliARQ9OydE/mkm-20260624"

Write-Host ""
Write-Host "=== Clinic LOI Figma MCP auto-apply setup ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "A) Remote (recommended): Cursor chat -> /add-plugin figma -> Allow Figma OAuth"
Write-Host "B) Desktop: Figma app -> Preferences -> Enable Local MCP Server -> restart if needed"
Write-Host ""
Write-Host "Then: Cursor Settings -> MCP -> figma or figma-desktop GREEN"
Write-Host "Then: chat '다시 자동적용' (agent calls use_figma)"
Write-Host ""

& py (Join-Path $root "scripts/build_clinic_loi_figma_mcp_apply_handoff_v1.py")
Start-Process $figmaUrl

try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:3845/mcp" -Method GET -TimeoutSec 2 -UseBasicParsing
    Write-Host "figma-desktop MCP: UP ($($r.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "figma-desktop MCP: DOWN (enable in Figma desktop Preferences)" -ForegroundColor Yellow
}

exit 0
