# Push manifest URLs + files to Fusion Insight Hub (NotebookLM) via nlm CLI.
#
# Fusion vs B-track: the Python B-track chain (build_btrack_llm_input_bundle / generate_* / eval_*)
# is separate from this script — same repo knowledge, not one fused executable unless you chain
# scripts yourself. This push is OPS/NotebookLM ingestion only.
#
# File uploads: `nlm source add --file` maps to APIs that expect supported binary types (e.g. PDF).
# Markdown/JSON/JSONL/YAML/CSV succeed reliably via `--text` (-t) for modest sizes; see $MaxTextBytesForPaste.
# On Windows, `-t` payload also hits CreateProcess command-line length limits, so guard with $MaxTextCharsForCli.
param(
  [string]$NotebookId = "71f55a03-09d0-411f-b365-0ce2a2064c24",
  [string]$ManifestPath = "C:\workspace\reports\notebooklm_fusion_hub_bulk_manifest.json",
  [string]$LogPath = "C:\workspace\reports\notebooklm_fusion_hub_bulk_push.log",
  [long]$MaxTextBytesForPaste = 409600,
  [int]$MaxTextCharsForCli = 12000,
  [int]$MaxNotebookSources = 300
)
$ErrorActionPreference = "Continue"
if (-not (Test-Path $ManifestPath)) {
  Write-Error "Manifest not found: $ManifestPath — run Build-NotebooklmFusionHubBulkManifest.ps1 first."
  exit 1
}
$m = Get-Content -Raw -Path $ManifestPath -Encoding utf8 | ConvertFrom-Json
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== Push start $ts ===" | Out-File -FilePath $LogPath -Encoding utf8
# URLs (single invocation, multiple -u)
$urlArgs = @("source", "add", $NotebookId)
foreach ($u in $m.urls) {
  $urlArgs += "-u"
  $urlArgs += $u
}
try {
  & nlm @urlArgs 2>&1 | Tee-Object -FilePath $LogPath -Append
} catch {
  $_ | Out-File -FilePath $LogPath -Append
}
$sourceCount = -1
try {
  $rawSources = (& nlm source list $NotebookId 2>$null | Out-String)
  $parsedSources = $rawSources | ConvertFrom-Json
  $sourceCount = @($parsedSources).Count
} catch {}
if ($sourceCount -ge 0) {
  "[source_count] current=$sourceCount max=$MaxNotebookSources" | Tee-Object -FilePath $LogPath -Append
}
$remainingSlots = if ($sourceCount -ge 0) { [Math]::Max(0, $MaxNotebookSources - $sourceCount) } else { [int]::MaxValue }
if ($remainingSlots -eq 0) {
  "[STOP] Notebook source cap reached. Skip file uploads." | Tee-Object -FilePath $LogPath -Append
  $ts2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "=== Done $ts2 ok=0 fail=0 ===" | Tee-Object -FilePath $LogPath -Append
  exit 0
}
$ok = 0
$fail = 0
$n = 0
foreach ($f in $m.files) {
  if ($ok -ge $remainingSlots) {
    "[STOP] Remaining slots exhausted after $ok successful file uploads." | Tee-Object -FilePath $LogPath -Append
    break
  }
  $n++
  if (-not (Test-Path -LiteralPath $f)) {
    "[SKIP missing] $f" | Tee-Object -FilePath $LogPath -Append
    $fail++
    continue
  }
  try {
    $ext = [System.IO.Path]::GetExtension($f).ToLowerInvariant()
    $textExts = @(".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".csv", ".mdown", ".log", ".html", ".htm")
    $fi = Get-Item -LiteralPath $f
    $useText = ($textExts -contains $ext) -and ($fi.Length -le $MaxTextBytesForPaste) -and ($fi.Length -gt 0)
    if ($ext -eq ".pdf") {
      & nlm source add $NotebookId --file $f 2>&1 | Tee-Object -FilePath $LogPath -Append
    } elseif ($useText) {
      $raw = [System.IO.File]::ReadAllText($f, [System.Text.UTF8Encoding]::new($false))
      if ($raw.Length -gt $MaxTextCharsForCli) {
        "[SKIP too long for CLI -t] $f ($($raw.Length) chars; max $MaxTextCharsForCli)" | Tee-Object -FilePath $LogPath -Append
        $fail++
        continue
      }
      $title = $fi.Name
      & nlm source add $NotebookId -t $raw --title $title 2>&1 | Tee-Object -FilePath $LogPath -Append
    } else {
      if (($textExts -contains $ext) -and ($fi.Length -gt $MaxTextBytesForPaste)) {
        "[SKIP too large for -t] $f ($($fi.Length) bytes; max $MaxTextBytesForPaste)" | Tee-Object -FilePath $LogPath -Append
        $fail++
        continue
      }
      & nlm source add $NotebookId --file $f 2>&1 | Tee-Object -FilePath $LogPath -Append
    }
    if ($LASTEXITCODE -eq 0) { $ok++ } else { "[FAIL nlm] $f" | Tee-Object -FilePath $LogPath -Append; $fail++ }
  } catch {
    "[ERR] $f : $_" | Tee-Object -FilePath $LogPath -Append
    $fail++
  }
  if (($n % 25) -eq 0) {
    "[progress] $n / $($m.files.Count) files" | Tee-Object -FilePath $LogPath -Append
  }
}
$ts2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== Done $ts2 ok=$ok fail=$fail ===" | Tee-Object -FilePath $LogPath -Append
