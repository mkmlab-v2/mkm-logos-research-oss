# Second pass: add MD/TXT/CSV only until ~300 sources (NotebookLM file-type limits).
param(
  [string]$NotebookId = "71f55a03-09d0-411f-b365-0ce2a2064c24",
  [int]$MaxAdd = 190,
  [long]$MaxBytes = 40MB
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
$added = 0
$fail = 0
foreach ($f in $files) {
  if ($added -ge $MaxAdd) { break }
  $null = & nlm source add $NotebookId --file $f.FullName 2>&1
  if ($LASTEXITCODE -eq 0) { $added++ } else { $fail++ }
  if ((($added + $fail) % 50) -eq 0) {
    Write-Output "progress added=$added fail=$fail last=$($f.Name)"
  }
}
Write-Output "TOPUP_DONE added=$added fail=$fail scanned=$($files.Count)"
