# MKM designlang MCP on-demand launcher (Design lane PoC).
# Does NOT modify .cursor/mcp.json core lean profile — use per-session or paste fragment.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-DesignlangMcpOnDemand_v1.ps1
#   powershell -File scripts\Invoke-DesignlangMcpOnDemand_v1.ps1 -Url https://stripe.com -Name stripe-com
#   powershell -File scripts\Invoke-DesignlangMcpOnDemand_v1.ps1 -OutputDir reports\designlang_poc_v1\jema-ai-com -McpOnly
#
param(
    [string]$Url = '',
    [string]$Name = '',
    [string]$OutputRoot = 'reports/designlang_poc_v1',
    [string]$OutputDir = '',
    [switch]$McpOnly,
    [switch]$SkipExtract
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

function Write-Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }

if (-not $OutputDir) {
    if (-not $Name) {
        if ($Url) {
            try { $Name = ([uri]$Url).Host.Replace('.', '-') } catch { $Name = 'design-extract' }
        } else {
            $Name = 'jema-ai-com'
            if (-not $Url) { $Url = 'https://jema-ai.com' }
        }
    }
    $OutputDir = Join-Path $Root (Join-Path $OutputRoot $Name)
}

Write-Step "OutputDir: $OutputDir"

if (-not $McpOnly -and -not $SkipExtract) {
    if (-not $Url) {
        throw 'Provide -Url or -OutputDir with existing extraction, or -McpOnly.'
    }
    Write-Step "Extracting: $Url"
    $extractArgs = @(
        '--yes', 'designlang', $Url,
        '-o', $OutputDir,
        '-n', $Name
    )
    & npx @extractArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: designlang exit $LASTEXITCODE (files may still exist; known tail TypeError on agent-rules)" -ForegroundColor Yellow
    }
}

if (-not (Test-Path $OutputDir)) {
    throw "Extraction dir missing: $OutputDir"
}

$fragmentPath = Join-Path $Root 'reports/designlang_poc_v1/designlang_mcp_on_demand_fragment.json'
$fragment = @{
    schema = 'designlang_mcp_on_demand_fragment_v1'
    note = 'Paste into Cursor MCP settings ONLY for a Design session. Remove after. Do not commit as core lean profile.'
    mcpServers = @{
        designlang = @{
            command = 'npx'
            args = @('-y', 'designlang', 'mcp', '--output-dir', ($OutputDir -replace '\\', '/'))
        }
    }
} | ConvertTo-Json -Depth 6
$fragment | Set-Content -Path $fragmentPath -Encoding utf8

Write-Step "Wrote fragment: $fragmentPath"
Write-Host ''
Write-Host 'Next (manual):' -ForegroundColor Green
Write-Host '  1. Cursor Settings -> MCP -> add server from fragment (or merge designlang block)'
Write-Host '  2. Reload Window -> new chat'
Write-Host "  3. MCP serves extraction at: $OutputDir"
Write-Host ''
Write-Host 'Stdio probe (blocks until Ctrl+C):' -ForegroundColor DarkGray
Write-Host "  npx -y designlang mcp --output-dir `"$OutputDir`""

exit 0
