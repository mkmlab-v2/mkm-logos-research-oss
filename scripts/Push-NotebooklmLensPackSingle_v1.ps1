<#
.SYNOPSIS
  Push one lens folder from reports/notebooklm_lens_packs_v1/<Lens> via nlm CLI.
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$Lens,
  [string]$WorkspaceRoot = "",
  [string]$NotebookMapPath = "",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  $WorkspaceRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
}
if (-not $NotebookMapPath) {
  $NotebookMapPath = Join-Path $WorkspaceRoot "reports\notebooklm_lens_packs_v1\notebook_ids.json"
}
if (-not (Get-Command nlm -ErrorAction SilentlyContinue)) {
  throw "nlm CLI not on PATH"
}
$raw = Get-Content -LiteralPath $NotebookMapPath -Raw -Encoding UTF8 | ConvertFrom-Json
$nb = [string]$raw.lens_notebook_id.$($Lens)
if ([string]::IsNullOrWhiteSpace($nb)) {
  throw "No notebook id for lens '$Lens' in $NotebookMapPath"
}
$dir = Join-Path $WorkspaceRoot "reports\notebooklm_lens_packs_v1\$Lens"
if (-not (Test-Path -LiteralPath $dir)) {
  throw "Pack dir missing: $dir — run build_notebooklm_lens_source_packs_v1.py"
}
$tmp = Join-Path $WorkspaceRoot "reports\tmp_nl_lens_upload"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

$existing = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
try {
  $nbRaw = (& nlm notebook get $nb --json 2>$null | Out-String)
  if (-not [string]::IsNullOrWhiteSpace($nbRaw)) {
    $nbDoc = $nbRaw | ConvertFrom-Json
    $nbVal = if ($nbDoc.value) { $nbDoc.value } else { $nbDoc }
    @($nbVal.sources) | ForEach-Object {
      if ($_.title) { [void]$existing.Add([string]$_.title) }
    }
  }
}
catch { }

$ok = 0
$skip = 0
$fail = 0
Get-ChildItem -LiteralPath $dir -File | Sort-Object Name | ForEach-Object {
  $title = $_.Name
  if ($title.Length -gt 120) { $title = $title.Substring(0, 120) }
  $ext = $_.Extension.ToLowerInvariant()
  $uploadPath = $_.FullName
  $nlmTitle = $title
  if ($ext -in @(".json", ".jsonl", ".yaml", ".yml")) {
    if ($ext -eq ".json") { $nlmTitle = "$title (text)" }
    $uploadPath = Join-Path $tmp ($_.Name + ".txt")
    [System.IO.File]::WriteAllText(
      $uploadPath,
      [System.IO.File]::ReadAllText($_.FullName),
      (New-Object System.Text.UTF8Encoding $false)
    )
  }
  if ($existing.Contains($title) -or $existing.Contains($nlmTitle)) {
    Write-Host "[SKIP exists] $nlmTitle"
    $script:skip++
    return
  }
  if ($DryRun) {
    Write-Host "[DRY] nlm source add $nb --file `"$uploadPath`" --title `"$nlmTitle`" --wait"
    $script:ok++
    return
  }
  Write-Host "[ADD] $nlmTitle"
  & nlm source add $nb --file $uploadPath --title $nlmTitle --wait
  if ($LASTEXITCODE -eq 0) {
    $script:ok++
    [void]$existing.Add($nlmTitle)
  }
  else {
    Write-Host "[FAIL exit=$LASTEXITCODE] $nlmTitle" -ForegroundColor Red
    $script:fail++
  }
  Start-Sleep -Milliseconds 500
}
Write-Host "DONE lens=$Lens notebook=$nb ok=$ok skip=$skip fail=$fail"
if ($fail -gt 0) { exit 1 }
exit 0
