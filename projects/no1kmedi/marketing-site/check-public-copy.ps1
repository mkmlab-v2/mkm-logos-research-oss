# Fail if banned phrases appear in user-facing site files (UTF-8).
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$bannedFile = Join-Path $root "banned-public-phrases.txt"
if (-not (Test-Path $bannedFile)) { Write-Host "OK (no banlist)"; exit 0 }
$patterns = Get-Content $bannedFile -Encoding UTF8 | Where-Object { $_ -notmatch "^\s*#" -and $_.Trim().Length -gt 0 } | ForEach-Object { $_.Trim() }
$targets = @("index.html", "styles.css", "app.js")
$failed = $false
foreach ($rel in $targets) {
  $path = Join-Path $root $rel
  if (-not (Test-Path $path)) { continue }
  $text = Get-Content $path -Raw -Encoding UTF8
  foreach ($p in $patterns) {
    if ($text.Contains($p)) {
      Write-Host "BANNED in ${rel}: $p"
      $failed = $true
    }
  }
}
if ($failed) { exit 1 }
Write-Host "OK: no banned phrases in marketing-site HTML/CSS/JS."
