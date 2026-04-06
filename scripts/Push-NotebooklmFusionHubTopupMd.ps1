# Second pass: add MD/TXT/CSV only until ~300 sources (NotebookLM file-type limits).
# Use --text (-t) for these types; `nlm source add --file` often fails for .md/.csv (API expects PDF-like uploads).
param(
  [string]$NotebookId = "71f55a03-09d0-411f-b365-0ce2a2064c24",
  [int]$MaxAdd = 190,
  [long]$MaxBytes = 40MB,
  [long]$MaxTextBytesForPaste = 409600,
  [int]$MaxTextCharsForCli = 12000,
  [int]$MaxNotebookSources = 300
)
$ErrorActionPreference = "Continue"
$dirs = @(
  "C:\workspace\docs",
  "C:\workspace\memory\obsidian_vault",
  "C:\workspace\data\corpus\ijeoma",
  "C:\workspace\data\myeongni",
  "C:\workspace\projects\bitcoin-trading\docs"
)
$ext = @("*.md", "*.txt", "*.csv")
$all = New-Object System.Collections.Generic.List[System.IO.FileInfo]
foreach ($d in $dirs) {
  if (-not (Test-Path $d)) { continue }
  foreach ($e in $ext) {
    Get-ChildItem -Path $d -Filter $e -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { $all.Add($_) }
  }
}
# Exclude stub noise (e.g. projects/mkm *.py.md) — never bulk-ingest training stubs into NotebookLM.
$files = $all | Where-Object { $_.Length -lt $MaxBytes -and $_.Name -notmatch '\.py\.md$' } | Sort-Object FullName -Unique
$sourceCount = -1
try {
  $rawSources = (& nlm source list $NotebookId 2>$null | Out-String)
  $parsedSources = $rawSources | ConvertFrom-Json
  $sourceCount = @($parsedSources).Count
} catch {}
if ($sourceCount -ge 0) {
  Write-Output "[source_count] current=$sourceCount max=$MaxNotebookSources"
}
$remainingSlots = if ($sourceCount -ge 0) { [Math]::Max(0, $MaxNotebookSources - $sourceCount) } else { $MaxAdd }
if ($remainingSlots -le 0) {
  Write-Output "TOPUP_DONE added=0 fail=0 scanned=$($files.Count) (cap reached)"
  exit 0
}
$effectiveMaxAdd = [Math]::Min($MaxAdd, $remainingSlots)
$added = 0
$fail = 0
foreach ($f in $files) {
  if ($added -ge $effectiveMaxAdd) { break }
  $p = $f.FullName
  if ($f.Length -gt $MaxTextBytesForPaste) {
    Write-Output "SKIP too large for -t: $($f.Name) ($($f.Length) bytes)"
    $fail++
    continue
  }
  if ($f.Length -eq 0) { continue }
  $raw = [System.IO.File]::ReadAllText($p, [System.Text.UTF8Encoding]::new($false))
  if ($raw.Length -gt $MaxTextCharsForCli) {
    Write-Output "SKIP too long for CLI -t: $($f.Name) ($($raw.Length) chars)"
    $fail++
    continue
  }
  $null = & nlm source add $NotebookId -t $raw --title $f.Name 2>&1
  if ($LASTEXITCODE -eq 0) { $added++ } else { Write-Output "[FAIL nlm] $($f.FullName)"; $fail++ }
  if ((($added + $fail) % 50) -eq 0) {
    Write-Output "progress added=$added fail=$fail last=$($f.Name)"
  }
}
Write-Output "TOPUP_DONE added=$added fail=$fail scanned=$($files.Count)"
