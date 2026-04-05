# Build URL + file manifest for Fusion Insight Hub bulk source_add (max ~300 sources).
$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$maxPerFile = 45MB
$maxTotalFiles = 260
$urls = @(
  "https://arxiv.org/abs/2603.19312",
  "https://arxiv.org/abs/2411.10668",
  "https://arxiv.org/abs/2010.14476",
  "https://www.kaggle.com/competitions/vesuvius-challenge-ink-detection",
  "https://www.kaggle.com/competitions/commonlitreadabilityprize",
  "https://www.kaggle.com/competitions/deep-past-initiative-machine-translation",
  "https://en.wikipedia.org/wiki/Four_Pillars_of_Destiny",
  "https://en.wikipedia.org/wiki/Korean_calendar",
  "https://en.wikipedia.org/wiki/Sexagenary_cycle",
  "https://en.wikipedia.org/wiki/Lunisolar_calendar",
  "https://en.wikipedia.org/wiki/Chinese_calendar",
  "https://ko.wikipedia.org/wiki/%EC%82%AC%EC%A3%BC",
  "https://ko.wikipedia.org/wiki/%EB%A7%8C%EC%84%B8%EB%A0%A5",
  "https://ko.wikipedia.org/wiki/%EC%82%AC%EC%A3%BC%EB%AA%85%EB%A6%AC%ED%95%99",
  "https://www.deadseascrolls.org.il/",
  "https://www.deadseascrolls.org.il/explore-the-archive"
)
$globs = @(
  "docs\final\*",
  "docs\external_research\*",
  "data\myeongni\*",
  "data\corpus\ijeoma\**\*.md",
  "data\corpus\ijeoma\**\*.json",
  "data\corpus\ijeoma\**\*.jsonl",
  "data\logos\reports\*",
  "data\regimes\*.json",
  "memory\obsidian_vault\SPIRIT\*.md"
)
$excludeName = @("*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.pdf", "*.zip", "*.parquet", "*.bin")
$files = New-Object System.Collections.Generic.List[string]
$seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($g in $globs) {
  Get-ChildItem -Path (Join-Path $root $g) -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    $n = $_.Name
    $skip = $false
    foreach ($ex in $excludeName) { if ($n -like $ex) { $skip = $true; break } }
    if ($skip) { return }
    if ($_.Length -gt $maxPerFile) { return }
    $fp = $_.FullName
    if ($seen.Add($fp)) { $files.Add($fp) }
  }
}
foreach ($x in @("AGENTS.md", "CLAUDE.md", ".cursorrules")) {
  $p = Join-Path $root $x
  if ((Test-Path $p) -and $seen.Add((Resolve-Path $p).Path)) { $files.Add((Resolve-Path $p).Path) }
}
$rank = {
  param($p)
  if ($p -match "\\docs\\final\\") { 0 }
  elseif ($p -match "\\data\\(myeongni|corpus|logos|regimes)\\") { 1 }
  else { 2 }
}
$sorted = $files | Sort-Object { & $rank $_ }, Length
$take = $sorted | Select-Object -First $maxTotalFiles
$out = [ordered]@{
  url_count  = $urls.Count
  file_count = $take.Count
  urls       = $urls
  files      = $take
}
$dest = Join-Path $root "reports\notebooklm_fusion_hub_bulk_manifest.json"
New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
$out | ConvertTo-Json -Depth 8 | Set-Content -Path $dest -Encoding utf8
Write-Output "Wrote $dest urls=$($urls.Count) files=$($take.Count)"
