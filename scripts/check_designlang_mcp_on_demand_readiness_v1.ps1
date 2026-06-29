# Verify designlang on-demand MCP fragment + extraction dir (no Cursor UI bind).
# Usage: powershell -File scripts\check_designlang_mcp_on_demand_readiness_v1.ps1

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$fragmentPath = Join-Path $Root 'reports/designlang_poc_v1/designlang_mcp_on_demand_fragment.json'
$outDir = Join-Path $Root 'reports/designlang_poc_v1/jema-ai-com'
$required = @(
    'jema-ai-com-design-tokens.json',
    'jema-ai-com-DESIGN.md',
    'jema-ai-com-mcp.json'
)

$report = [ordered]@{
    schema = 'designlang_mcp_on_demand_readiness_v1'
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    fragment_path = $fragmentPath.Replace('\', '/')
    output_dir = $outDir.Replace('\', '/')
    checks = @()
    ok = $true
}

if (-not (Test-Path $fragmentPath)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'scripts/Invoke-DesignlangMcpOnDemand_v1.ps1') -McpOnly -OutputDir $outDir | Out-Null
}

$report.fragment_exists = Test-Path $fragmentPath
if (-not $report.fragment_exists) { $report.ok = $false }

foreach ($name in $required) {
    $p = Join-Path $outDir $name
    $exists = Test-Path $p
    $report.checks += @{ id = $name; ok = $exists; path = $p.Replace('\', '/') }
    if (-not $exists) { $report.ok = $false }
}

try {
    $null = & npx --yes designlang --version 2>&1
    $report.designlang_cli = $true
} catch {
    $report.designlang_cli = $false
    $report.ok = $false
}

$outJson = Join-Path $Root 'reports/designlang_mcp_on_demand_readiness_v1_latest.json'
$report | ConvertTo-Json -Depth 6 | Set-Content -Path $outJson -Encoding utf8

Write-Host "designlang MCP readiness: ok=$($report.ok) -> $outJson"
if (-not $report.ok) { exit 1 }
exit 0
