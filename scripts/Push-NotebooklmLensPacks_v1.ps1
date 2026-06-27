<#
.SYNOPSIS
  Push reports/notebooklm_lens_packs_v1/* into Google NotebookLM via `nlm source add` (CLI).

.DESCRIPTION
  Why not "fully automatic" from Vault/MCP alone:
  - Vault mirror only copies files to shared disk; Google does not ingest that folder into NL.
  - Cursor MCP `add_source` is per-call, chat-bound, and UI-locale sensitive (see notebooklm-mcp-session-bridge.mdc).

  This script uses the same **`nlm` CLI** path as `Push-NotebooklmFusionHubBulk.ps1` / `Push-AthenaUploadOnefileToNotebooklm.ps1`:
  `nlm source add <notebook_id> --file <path> --title <title> [--wait]`

  Prerequisites:
  - `nlm` on PATH (global `notebooklm-mcp` install; same Google profile you use for NL pushes).
  - Run `py scripts/build_notebooklm_lens_source_packs_v1.py` first (or the hybrid routine Phase 1).
  - Notebook map JSON (see -InitMap).

.PARAMETER WorkspaceRoot
  Repo root (default: parent of scripts/).

.PARAMETER NotebookMapPath
  JSON with `lens_notebook_id` object mapping lens folder names to NL notebook UUIDs.
  Default: <WorkspaceRoot>/reports/notebooklm_lens_packs_v1/notebook_ids.json

.PARAMETER InitMap
  Copy docs/final/notebooklm_lens_pack_push_map_v1.template.json -> default NotebookMapPath and exit 0.

.PARAMETER DryRun
  Print planned operations only (no `nlm` calls).

.PARAMETER MaxNotebookSources
  Stop adding when a notebook already has this many sources (default 300).

.PARAMETER SleepMs
  Delay between `nlm` invocations (default 400).

.PARAMETER Refresh
  Delete same-title sources before add (latest sync).

.PARAMETER LogPath
  Append log path (default reports/notebooklm_lens_pack_push_latest.log).
#>
param(
  [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
  [string]$NotebookMapPath = "",
  [switch]$InitMap,
  [switch]$DryRun,
  [int]$MaxNotebookSources = 300,
  [int]$SleepMs = 400,
  [string]$LogPath = "",
  [switch]$Refresh
)

$ErrorActionPreference = "Stop"
$LensKeys = @(
  "OPS_COMMAND_ANCHOR", "TRACKC_BIZ", "LENS_MYEONGNI",
  "LENS_SASANG", "LENS_LOGOS", "MKM_CORE_FACT", "COMPRESSION_BTRACK"
)

if (-not $NotebookMapPath) {
  $NotebookMapPath = Join-Path $WorkspaceRoot "reports\notebooklm_lens_packs_v1\notebook_ids.json"
}
if (-not $LogPath) {
  $LogPath = Join-Path $WorkspaceRoot "reports\notebooklm_lens_pack_push_latest.log"
}

$template = Join-Path $WorkspaceRoot "docs\final\notebooklm_lens_pack_push_map_v1.template.json"
$packRoot = Join-Path $WorkspaceRoot "reports\notebooklm_lens_packs_v1"

if ($InitMap) {
  if (-not (Test-Path -LiteralPath $template)) {
    throw "Template missing: $template"
  }
  $dir = Split-Path -Parent $NotebookMapPath
  if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
  }
  Copy-Item -LiteralPath $template -Destination $NotebookMapPath -Force
  Write-Host "Wrote map template -> $NotebookMapPath (edit UUIDs if you split notebooks)" -ForegroundColor Green
  exit 0
}

if (-not $DryRun -and -not (Get-Command nlm -ErrorAction SilentlyContinue)) {
  throw "nlm CLI not on PATH. Install global notebooklm-mcp (npm i -g notebooklm-mcp@<version>) and ensure nlm is available, same as Push-NotebooklmFusionHubBulk.ps1."
}

if (-not (Test-Path -LiteralPath $NotebookMapPath)) {
  throw "Notebook map not found: $NotebookMapPath — run: powershell -File scripts/Push-NotebooklmLensPacks_v1.ps1 -InitMap"
}

if (-not (Test-Path -LiteralPath $packRoot)) {
  throw "Lens pack root missing: $packRoot — run py scripts/build_notebooklm_lens_source_packs_v1.py first."
}

$raw = Get-Content -LiteralPath $NotebookMapPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $raw.lens_notebook_id) {
  throw "Invalid map JSON: missing lens_notebook_id object in $NotebookMapPath"
}

$map = @{}
foreach ($k in $LensKeys) {
  $nid = $raw.lens_notebook_id.$($k)
  if ([string]::IsNullOrWhiteSpace([string]$nid)) {
    throw "Map missing or empty notebook id for lens '$k' in $NotebookMapPath"
  }
  $map[$k] = [string]$nid
}

$logDir = Split-Path -Parent $LogPath
if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
  New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== Push-NotebooklmLensPacks_v1 start $ts dry_run=$DryRun ===" | Out-File -FilePath $LogPath -Encoding utf8

function Get-SourceList([string]$notebookId) {
  try {
    $rawList = (& nlm source list $notebookId 2>$null | Out-String)
    if ([string]::IsNullOrWhiteSpace($rawList)) { return @() }
    return @($rawList | ConvertFrom-Json)
  }
  catch {
    return @()
  }
}

function Get-SourceCount([string]$notebookId) {
  $parsed = Get-SourceList $notebookId
  if ($parsed.Count -eq 0) {
    $rawList = (& nlm source list $notebookId 2>$null | Out-String)
    if ([string]::IsNullOrWhiteSpace($rawList)) { return -1 }
  }
  return @($parsed).Count
}

function Get-ExistingTitleSet([string]$notebookId) {
  $set = [System.Collections.Generic.HashSet[string]]::new(
    [StringComparer]::OrdinalIgnoreCase
  )
  foreach ($s in (Get-SourceList $notebookId)) {
    if ($s.title) { [void]$set.Add([string]$s.title) }
  }
  return $set
}

# Per-notebook remaining slots + existing titles (skip duplicate adds).
$remainingByNotebook = @{}
$existingTitlesByNotebook = @{}
foreach ($nb in ($map.Values | Select-Object -Unique)) {
  if ($DryRun) {
    $remainingByNotebook[$nb] = [int]::MaxValue
    $existingTitlesByNotebook[$nb] = $null
    "[DRY][notebook $nb] skip live source count" | Tee-Object -FilePath $LogPath -Append
    continue
  }
  $existingTitlesByNotebook[$nb] = Get-ExistingTitleSet $nb
  $c = Get-SourceCount $nb
  if ($c -ge 0) {
    $rem = [Math]::Max(0, $MaxNotebookSources - $c)
    $remainingByNotebook[$nb] = $rem
    "[notebook $nb] current_sources=$c remaining_slots=$rem" | Tee-Object -FilePath $LogPath -Append
  }
  else {
    $remainingByNotebook[$nb] = [int]::MaxValue
    "[notebook $nb] current_sources=unknown remaining_slots=unbounded" | Tee-Object -FilePath $LogPath -Append
  }
}

$tmpUploadDir = Join-Path $WorkspaceRoot "reports\tmp_nl_lens_upload"
if (-not (Test-Path -LiteralPath $tmpUploadDir)) {
  New-Item -ItemType Directory -Path $tmpUploadDir -Force | Out-Null
}

function Remove-SourceByTitle([string]$notebookId, [string]$title) {
  $parsed = Get-SourceList $notebookId
  $ids = @($parsed | Where-Object { [string]$_.title -eq $title } | ForEach-Object { [string]$_.id })
  if ($ids.Count -eq 0) { return 0 }
  & nlm source delete @ids --confirm 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { return $ids.Count }
  return 0
}

function Resolve-NlmUploadFile {
  param([System.IO.FileInfo]$FileInfo, [string]$DisplayTitle)
  $ext = $FileInfo.Extension.ToLowerInvariant()
  if ($ext -in @(".json", ".jsonl", ".yaml", ".yml")) {
    $uploadTitle = if ($ext -eq ".json") { "$DisplayTitle (text)" } else { $DisplayTitle }
    $tmpPath = Join-Path $tmpUploadDir ($FileInfo.Name + ".txt")
    [System.IO.File]::WriteAllText($tmpPath, [System.IO.File]::ReadAllText($FileInfo.FullName), (New-Object System.Text.UTF8Encoding $false))
    return @{ Path = $tmpPath; Title = $uploadTitle }
  }
  return @{ Path = $FileInfo.FullName; Title = $DisplayTitle }
}

$ok = 0
$fail = 0
$skip = 0
foreach ($lens in $LensKeys) {
  $dir = Join-Path $packRoot $lens
  if (-not (Test-Path -LiteralPath $dir)) {
    "[SKIP no dir] $lens" | Tee-Object -FilePath $LogPath -Append
    continue
  }
  $nid = $map[$lens]
  $files = Get-ChildItem -LiteralPath $dir -File | Sort-Object Name
  foreach ($fi in $files) {
    if ($fi.Name -eq "README.md") { continue }
    $title = $fi.Name
    if ($title.Length -gt 120) { $title = $title.Substring(0, 120) }
    $rem = $remainingByNotebook[$nid]
    if ($rem -le 0) {
      "[STOP cap] notebook=$nid lens=$lens file=$($fi.Name)" | Tee-Object -FilePath $LogPath -Append
      break
    }
    $upload = Resolve-NlmUploadFile -FileInfo $fi -DisplayTitle $title
    $full = $upload.Path
    $nlmTitle = $upload.Title
    $existing = $existingTitlesByNotebook[$nid]
    if (-not $Refresh -and $existing -and ($existing.Contains($title) -or $existing.Contains($nlmTitle))) {
      "[SKIP exists] $lens $nlmTitle" | Tee-Object -FilePath $LogPath -Append
      $skip++
      continue
    }
    if ($Refresh -and -not $DryRun) {
      $del1 = Remove-SourceByTitle $nid $title
      $del2 = Remove-SourceByTitle $nid $nlmTitle
      if (($del1 + $del2) -gt 0) {
        "[REFRESH deleted] $lens $nlmTitle count=$($del1 + $del2)" | Tee-Object -FilePath $LogPath -Append
      }
    }
    if ($DryRun) {
      "[DRY] nlm source add $nid --file `"$full`" --title `"$nlmTitle`" --wait" | Tee-Object -FilePath $LogPath -Append
      $ok++
      continue
    }
    try {
      & nlm source add $nid --file $full --title $nlmTitle --wait 2>&1 | Tee-Object -FilePath $LogPath -Append
      if ($LASTEXITCODE -eq 0) {
        $ok++
        $remainingByNotebook[$nid] = $rem - 1
        if ($null -ne $existing) {
          try { [void]$existing.Add($nlmTitle) } catch { }
        }
      }
      else {
        "[FAIL nlm exit=$LASTEXITCODE] $lens $($fi.Name)" | Tee-Object -FilePath $LogPath -Append
        $fail++
      }
    }
    catch {
      "[ERR] $lens $($fi.Name) : $_" | Tee-Object -FilePath $LogPath -Append
      $fail++
    }
    Start-Sleep -Milliseconds $SleepMs
  }
}

$ts2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== Done $ts2 ok=$ok skip=$skip fail=$fail ===" | Tee-Object -FilePath $LogPath -Append
if ($fail -gt 0) { exit 1 }
exit 0
