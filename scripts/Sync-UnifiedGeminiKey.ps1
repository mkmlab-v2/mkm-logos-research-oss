param(
  [string]$SourceEnv = "C:\workspace\.env",
  [string]$GeminiApiKey = "",
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-EnvValue {
  param(
    [string]$Path,
    [string]$Name
  )
  if (-not (Test-Path $Path)) { return $null }
  $line = Get-Content -Path $Path | Where-Object { $_ -match "^\s*$Name\s*=" } | Select-Object -First 1
  if (-not $line) { return $null }
  return ($line -replace "^\s*$Name\s*=\s*", "").Trim()
}

function Set-Or-AppendLine {
  param(
    [string]$Path,
    [string]$Name,
    [string]$Value
  )
  $lines = @()
  if (Test-Path $Path) {
    $lines = Get-Content -Path $Path
  }
  $target = "$Name=$Value"
  $updated = $false
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^\s*$Name\s*=") {
      $lines[$i] = $target
      $updated = $true
      break
    }
  }
  if (-not $updated) {
    if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -ne "") {
      $lines += ""
    }
    $lines += $target
  }
  return $lines
}

function Write-EnvFile {
  param(
    [string]$Path,
    [string[]]$Lines
  )
  $parent = Split-Path -Parent $Path
  if (-not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent | Out-Null
  }
  [System.IO.File]::WriteAllLines($Path, $Lines, [System.Text.UTF8Encoding]::new($false))
}

$sourceCandidates = @($SourceEnv, "C:\workspace\projects\mkm\mkm-life\.env.local", "C:\workspace\projects\no1kmedi\.env.local")

$resolvedSource = $null
$geminiKey = $GeminiApiKey.Trim()
if ($geminiKey) {
  $resolvedSource = "param:GeminiApiKey"
} else {
  $envKey = ($env:GEMINI_API_KEY, $env:GOOGLE_API_KEY | Where-Object { $_ -and $_.Trim() } | Select-Object -First 1)
  if ($envKey) {
    $geminiKey = $envKey.Trim()
    $resolvedSource = "process_env"
  }
}

if (-not $geminiKey) {
  foreach ($candidate in $sourceCandidates) {
    $v = Get-EnvValue -Path $candidate -Name "GEMINI_API_KEY"
    if (-not $v) { $v = Get-EnvValue -Path $candidate -Name "GOOGLE_API_KEY" }
    if ($v) {
      $resolvedSource = $candidate
      $geminiKey = $v
      break
    }
  }
}

if (-not $geminiKey) {
  throw "GEMINI_API_KEY/GOOGLE_API_KEY not found in source candidates: $($sourceCandidates -join ', ')"
}

$targets = @(
  "C:\workspace\projects\mkm\mkm-life\.env.local",
  "C:\workspace\projects\no1kmedi\.env.local"
)

foreach ($target in $targets) {
  $next = Set-Or-AppendLine -Path $target -Name "GEMINI_API_KEY" -Value $geminiKey
  $next = Set-Or-AppendLine -Path $target -Name "GOOGLE_API_KEY" -Value $geminiKey
  if ($DryRun) {
    Write-Host "[DRY-RUN] would update: $target"
    continue
  }
  Write-EnvFile -Path $target -Lines $next
  Write-Host "updated: $target"
}

Write-Host "source: $resolvedSource"
Write-Host "done: unified Gemini key synced to mkm-life/no1kmedi"
