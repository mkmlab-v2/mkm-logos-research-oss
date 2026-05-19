<#
.SYNOPSIS
  Copy GEMINI/GOOGLE API key from child .env.local into workspace root .env (never prints key).

.DESCRIPTION
  Sources (first hit): process env, projects/no1kmedi/.env.local, projects/mkm/mkm-life/.env.local.
  Sets GEMINI_API_KEY, MKM_MARKETING_GEMINI_ALLOWED=1, optional MKM_AUDIO_GEMINI_MODEL.
  Does not commit; .env is gitignored.
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = if ($WorkspaceRoot) {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
} else {
    "C:\workspace"
}

function Get-EnvValue {
    param([string]$Path, [string]$Name)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match "^\s*$Name\s*=" } | Select-Object -First 1
    if (-not $line) { return $null }
    return ($line -replace "^\s*$Name\s*=\s*", "").Trim().Trim('"').Trim("'")
}

function Set-Or-AppendLine {
    param([string[]]$Lines, [string]$Name, [string]$Value)
    $target = "$Name=$Value"
    $updated = $false
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match "^\s*#?\s*$Name\s*=") {
            $Lines[$i] = $target
            $updated = $true
            break
        }
    }
    if (-not $updated) {
        if ($Lines.Count -gt 0 -and $Lines[-1] -ne "") { $Lines += "" }
        $Lines += $target
    }
    return ,$Lines
}

$sources = @(
    (Join-Path $root "projects\no1kmedi\.env.local"),
    (Join-Path $root "projects\mkm\mkm-life\.env.local"),
    (Join-Path $root ".env")
)

$key = $null
$resolved = $null
foreach ($k in @("GEMINI_API_KEY", "GOOGLE_API_KEY")) {
    $v = [Environment]::GetEnvironmentVariable($k, "Process")
    if ($v -and $v.Trim().Length -gt 10) { $key = $v.Trim(); $resolved = "process:$k"; break }
}
if (-not $key) {
    foreach ($path in $sources) {
        foreach ($name in @("GEMINI_API_KEY", "GOOGLE_API_KEY")) {
            $v = Get-EnvValue -Path $path -Name $name
            if ($v -and $v.Length -gt 10) { $key = $v; $resolved = "${path}:${name}"; break }
        }
        if ($key) { break }
    }
}
if (-not $key) {
    throw "GEMINI_API_KEY not found in no1kmedi/mkm-life .env.local or process env."
}

$envPath = Join-Path $root ".env"
$lines = if (Test-Path -LiteralPath $envPath) { @(Get-Content -LiteralPath $envPath) } else { @() }

$lines = Set-Or-AppendLine -Lines $lines -Name "GEMINI_API_KEY" -Value $key
$lines = Set-Or-AppendLine -Lines $lines -Name "MKM_MARKETING_GEMINI_ALLOWED" -Value "1"
if (-not (Get-EnvValue -Path $envPath -Name "MKM_AUDIO_GEMINI_MODEL")) {
    $lines = Set-Or-AppendLine -Lines $lines -Name "MKM_AUDIO_GEMINI_MODEL" -Value "gemini-2.5-flash"
}

# Comment duplicate GOOGLE_API_KEY in root .env to reduce google-genai warning
$newLines = foreach ($line in $lines) {
    if ($line -match '^\s*GOOGLE_API_KEY\s*=') { "# GOOGLE_API_KEY=  # use GEMINI_API_KEY only" } else { $line }
}

if ($DryRun) {
    Write-Host "[DRY-RUN] would update $envPath (source=$resolved)"
    exit 0
}

[System.IO.File]::WriteAllLines($envPath, $newLines, [System.Text.UTF8Encoding]::new($false))
Write-Host "updated: $envPath (GEMINI_API_KEY + MKM_MARKETING_GEMINI_ALLOWED=1)"
Write-Host "source: $resolved"
exit 0
