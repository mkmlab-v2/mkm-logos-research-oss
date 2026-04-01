# Hostinger API MCP — stdio JSON-RPC only on stdout (no Write-Host).
# Optional manual runner; Cursor should use .cursor/mcp.json (npx hostinger-api-mcp).
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"
if (-not $env:DEBUG) { $env:DEBUG = "false" }

$dot = "C:\workspace\.env"
if (Test-Path -LiteralPath $dot) {
    Get-Content -LiteralPath $dot -Encoding utf8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $key = $line.Substring(0, $eq).Trim()
        $val = $line.Substring($eq + 1).Trim()
        if ($val.Length -ge 2 -and (
                ($val.StartsWith([char]34) -and $val.EndsWith([char]34)) -or
                ($val.StartsWith([char]39) -and $val.EndsWith([char]39)))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        if (-not $key) { return }
        $cur = [Environment]::GetEnvironmentVariable($key, "Process")
        if ([string]::IsNullOrEmpty($cur)) {
            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
}

if (-not $env:API_TOKEN -and $env:HOSTINGER_API_TOKEN) {
    $env:API_TOKEN = $env:HOSTINGER_API_TOKEN
}

$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) { $npx = Get-Command npx -ErrorAction SilentlyContinue }
if (-not $npx) {
    throw "npx not found. Install Node.js (https://nodejs.org/) — hostinger-api-mcp needs Node 20+."
}
& $npx.Source -y hostinger-api-mcp --stdio
exit $LASTEXITCODE
