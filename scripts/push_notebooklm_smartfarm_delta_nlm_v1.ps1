param(
  [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
  [string]$NotebookId = "96865180-769e-4a77-89bb-5f03a8083ac3",
  [switch]$Refresh
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$pack = Join-Path $WorkspaceRoot "reports\notebooklm_smartfarm_geumsan_sync_pack_v1"
$index = Join-Path $pack "index.json"
if (-not (Test-Path -LiteralPath $index)) { throw "missing $index" }
$raw = Get-Content -LiteralPath $index -Raw -Encoding UTF8 | ConvertFrom-Json
$deltas = @($raw.delta_upload_recommended)
$have = @{}
$list = (& nlm source list $NotebookId 2>$null | Out-String)
if (-not [string]::IsNullOrWhiteSpace($list)) {
  foreach ($row in @($list | ConvertFrom-Json)) {
    $t = [string]$row.title
    if ($t) { $have[$t.Trim()] = $true }
  }
}
$ok = 0; $skip = 0; $fail = 0; $ref = 0
function Remove-TitleIfExists([string]$nb, [string]$title) {
  $rows = @()
  $list = (& nlm source list $nb 2>$null | Out-String)
  if (-not [string]::IsNullOrWhiteSpace($list)) { $rows = @($list | ConvertFrom-Json) }
  $ids = @($rows | Where-Object { [string]$_.title -eq $title } | ForEach-Object { [string]$_.id })
  if ($ids.Count -eq 0) { return 0 }
  & nlm source delete @ids --confirm 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { return $ids.Count }
  return 0
}
foreach ($f in $deltas) {
  $title = $f
  if ($f -like "*.json") { $title = "$f (text)" }
  if ($Refresh) {
    $ref += Remove-TitleIfExists $NotebookId $title
  } elseif ($have.ContainsKey($title)) {
    Write-Host "SKIP $title"
    $skip++
    continue
  }
  $path = Join-Path $pack $f
  if (-not (Test-Path -LiteralPath $path)) {
    Write-Host "MISSING $path"
    $fail++
    continue
  }
  if ($f -like "*.json") {
    $txt = Get-Content -LiteralPath $path -Raw -Encoding UTF8
    $tmpDir = Join-Path $WorkspaceRoot "reports\tmp_nl_lens_upload"
    if (-not (Test-Path -LiteralPath $tmpDir)) { New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null }
    $tmp = Join-Path $tmpDir ($f + ".txt")
    Set-Content -LiteralPath $tmp -Value $txt -Encoding UTF8 -NoNewline
    & nlm source add $NotebookId --file $tmp --title $title --wait
  } else {
    & nlm source add $NotebookId --file $path --title $title --wait
  }
  if ($LASTEXITCODE -eq 0) { $ok++ } else { $fail++ }
}
Write-Host "smartfarm delta ok=$ok skip=$skip fail=$fail refresh_deleted=$ref"
if ($fail -gt 0) { exit 1 }
exit 0
