# Push manifest URLs + files to Fusion Insight Hub (NotebookLM) via nlm CLI.
param(
  [string]$NotebookId = "71f55a03-09d0-411f-b365-0ce2a2064c24",
  [string]$ManifestPath = "C:\workspace\reports\notebooklm_fusion_hub_bulk_manifest.json",
  [string]$LogPath = "C:\workspace\reports\notebooklm_fusion_hub_bulk_push.log"
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
$ok = 0
$fail = 0
$n = 0
foreach ($f in $m.files) {
  $n++
  if (-not (Test-Path -LiteralPath $f)) {
    "[SKIP missing] $f" | Tee-Object -FilePath $LogPath -Append
    $fail++
    continue
  }
  try {
    & nlm source add $NotebookId --file $f 2>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -eq 0) { $ok++ } else { $fail++ }
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
