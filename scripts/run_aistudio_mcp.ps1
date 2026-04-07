# Google AI Studio (Gemini) MCP — stdio. Loads C:\workspace\.env into Process env, then npx aistudio-mcp-server.
# Ensures workspace .env wins over stale User env (fixes MCP "API key expired" when envFile is ignored).
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

# Drop inherited Process-scope keys so Cursor/host cannot leave a stale GEMINI before .env loads.
foreach ($k in @("GEMINI_API_KEY", "GOOGLE_API_KEY")) {
    [Environment]::SetEnvironmentVariable($k, $null, "Process")
}

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

# Sandbox / no .env: fall back to User-scope key (after sync_required_env_to_user.ps1).
if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "Process"))) {
    $ug = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")
    if (-not [string]::IsNullOrWhiteSpace($ug)) {
        [Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $ug.Trim(), "Process")
    }
}

# Last step before Node: re-apply GEMINI_API_KEY from .env only (overrides stale host-injected keys).
function Set-GeminiApiKeyFromDotenvLine([string]$line) {
    $line = $line.Trim()
    if (-not $line -or $line.StartsWith("#")) { return $false }
    if ($line -notmatch '^\s*GEMINI_API_KEY\s*=') { return $false }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return $false }
    $val = $line.Substring($eq + 1).Trim()
    if ($val.Length -ge 2 -and (
            ($val.StartsWith([char]34) -and $val.EndsWith([char]34)) -or
            ($val.StartsWith([char]39) -and $val.EndsWith([char]39)))) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    if ([string]::IsNullOrWhiteSpace($val)) { return $false }
    [Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $val, "Process")
    return $true
}
if (Test-Path -LiteralPath $dot) {
    $geminiFromFile = $false
    foreach ($line in Get-Content -LiteralPath $dot -Encoding utf8) {
        if (Set-GeminiApiKeyFromDotenvLine $line) { $geminiFromFile = $true }
    }
    if ($geminiFromFile) {
        [Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "Process")
    }
}

$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) { $npx = Get-Command npx -ErrorAction SilentlyContinue }
if (-not $npx) {
    throw "npx not found. Install Node.js — aistudio-mcp-server needs npx."
}
& $npx.Source -y aistudio-mcp-server
exit $LASTEXITCODE
