<#
.SYNOPSIS
  Push COMPRESSION_BTRACK + IJEOMA_BTRACK lens packs to NotebookLM via nlm CLI (commander-approved auto upload).

.NOTES
  Notebook IDs (SSOT pointers):
  - COMPRESSION_BTRACK -> MKM_CORE_INTELLIGENCE_V1 (aba1f8b1-...)
  - IJEOMA_BTRACK -> 이제마 B research (af639d3e-... per comp_ijeoma_btrack_nl_pack_v1.json)
#>
param(
  [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
  [switch]$DryRun,
  [int]$MaxNotebookSources = 300,
  [int]$SleepMs = 400,
  [long]$MaxTextBytesForPaste = 409600,
  [int]$MaxTextCharsForCli = 12000,
  [string]$LogPath = ""
)

$ErrorActionPreference = "Stop"
if (-not $LogPath) {
  $LogPath = Join-Path $WorkspaceRoot "reports\notebooklm_btrack_lens_pack_push_latest.log"
}

$packRoot = Join-Path $WorkspaceRoot "reports\notebooklm_lens_packs_v1"
$lensMap = @{
  "COMPRESSION_BTRACK" = "aba1f8b1-be62-4367-ac7f-b1a997bb77d4"
  "IJEOMA_BTRACK"      = "af639d3e-b455-4f3f-8e25-47f58d962c60"
}

if (-not $DryRun -and -not (Get-Command nlm -ErrorAction SilentlyContinue)) {
  throw "nlm CLI not on PATH. Install notebooklm-mcp globally (same profile as FusionHubBulk)."
}
if (-not (Test-Path -LiteralPath $packRoot)) {
  throw "Missing $packRoot — run: py scripts/build_notebooklm_lens_source_packs_v1.py"
}

$logDir = Split-Path -Parent $LogPath
if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
  New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== Push-NotebooklmBtrackLensPacks_v1 $ts dry_run=$DryRun ===" | Out-File -FilePath $LogPath -Encoding utf8

function Get-SourceCount([string]$notebookId) {
  try {
    $rawList = (& nlm source list $notebookId 2>$null | Out-String)
    if ([string]::IsNullOrWhiteSpace($rawList)) { return -1 }
    return @($rawList | ConvertFrom-Json).Count
  }
  catch { return -1 }
}

$textExts = @(".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".csv", ".html", ".htm")
$ok = 0
$fail = 0
$skip = 0

foreach ($lens in $lensMap.Keys) {
  $nid = $lensMap[$lens]
  $dir = Join-Path $packRoot $lens
  if (-not (Test-Path -LiteralPath $dir)) {
    "[SKIP no dir] $lens" | Tee-Object -FilePath $LogPath -Append
    continue
  }
  $remaining = if ($DryRun) { [int]::MaxValue } else {
    $c = Get-SourceCount $nid
    if ($c -ge 0) { [Math]::Max(0, $MaxNotebookSources - $c) } else { [int]::MaxValue }
  }
  "[lens $lens] notebook=$nid remaining_slots=$remaining" | Tee-Object -FilePath $LogPath -Append

  foreach ($fi in (Get-ChildItem -LiteralPath $dir -File | Sort-Object Name)) {
    if ($remaining -le 0) {
      "[STOP cap] $lens" | Tee-Object -FilePath $LogPath -Append
      break
    }
    $full = $fi.FullName
    $title = $fi.Name
    if ($title.Length -gt 120) { $title = $title.Substring(0, 120) }
    $ext = $fi.Extension.ToLowerInvariant()

    if ($DryRun) {
      "[DRY] $lens $title -> $nid" | Tee-Object -FilePath $LogPath -Append
      $ok++
      continue
    }

    try {
      if ($fi.Length -gt 8MB) {
        "[SKIP too large] $lens $title ($($fi.Length) bytes)" | Tee-Object -FilePath $LogPath -Append
        $skip++
        continue
      }
      # Prefer --file (avoids Windows CLI length limits on --text for JSON/MD).
      & nlm source add $nid -f $full --title $title --wait 2>&1 | Tee-Object -FilePath $LogPath -Append
      if ($LASTEXITCODE -eq 0) {
        $ok++
        $remaining--
      }
      else {
        "[FAIL exit=$LASTEXITCODE] $lens $title" | Tee-Object -FilePath $LogPath -Append
        $fail++
      }
    }
    catch {
      "[ERR] $lens $title : $_" | Tee-Object -FilePath $LogPath -Append
      $fail++
    }
    Start-Sleep -Milliseconds $SleepMs
  }
}

"=== Done ok=$ok fail=$fail skip=$skip ===" | Tee-Object -FilePath $LogPath -Append
if ($fail -gt 0) { exit 1 }
exit 0
