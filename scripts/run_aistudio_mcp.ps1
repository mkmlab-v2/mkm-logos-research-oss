# Google AI Studio (Gemini) MCP — stdio. Loads C:\workspace\.env into Process env, then npx aistudio-mcp-server.
# Ensures workspace .env wins over stale User env (fixes MCP "API key expired" when envFile is ignored).
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

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
        [Environment]::SetEnvironmentVariable($key, $val, "Process")
    }
}

# Prefer GEMINI_API_KEY when both exist (google-genai / server may pick GOOGLE otherwise).
if (-not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "Process"))) {
    [Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "Process")
}

$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) { $npx = Get-Command npx -ErrorAction SilentlyContinue }
if (-not $npx) {
    throw "npx not found. Install Node.js — aistudio-mcp-server needs npx."
}
& $npx.Source -y aistudio-mcp-server
exit $LASTEXITCODE
