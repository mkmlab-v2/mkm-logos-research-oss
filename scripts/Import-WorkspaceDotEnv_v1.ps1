<#
.SYNOPSIS
  Load workspace .env into Process scope (no value logging). Dot-source: . .\scripts\Import-WorkspaceDotEnv_v1.ps1
#>
param(
    [string]$WorkspaceRoot = ""
)

$root = if ($WorkspaceRoot) {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
} else {
    if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
        $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
    } else {
        (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    }
}

$dotEnv = Join-Path $root ".env"
if (-not (Test-Path -LiteralPath $dotEnv)) {
    return
}

$bytes = [System.IO.File]::ReadAllBytes($dotEnv)
$text = $null
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $text = $utf8.GetString($bytes, 3, $bytes.Length - 3)
}
elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
    $text = [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
}
else {
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $text = $utf8.GetString($bytes)
}

$count = 0
foreach ($rawLine in $text -split "`r?`n") {
    $line = $rawLine.Trim().TrimStart([char]0xFEFF)
    if (-not $line -or $line.StartsWith("#")) { continue }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { continue }
    $key = $line.Substring(0, $eq).Trim()
    $val = $line.Substring($eq + 1).Trim()
    if ($key.StartsWith("export ", [System.StringComparison]::OrdinalIgnoreCase)) {
        $key = $key.Substring(7).Trim()
    }
    if ($val.Length -ge 2 -and (
            ($val.StartsWith([char]34) -and $val.EndsWith([char]34)) -or
            ($val.StartsWith([char]39) -and $val.EndsWith([char]39)))) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    if (-not $key) { continue }
    [Environment]::SetEnvironmentVariable($key, $val, "Process")
    $count++
}
Write-Host "Dotenv: loaded $count keys from .env into Process (values not logged)." -ForegroundColor DarkGray
