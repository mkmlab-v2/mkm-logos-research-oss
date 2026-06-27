<#
.SYNOPSIS
  Upload COMPRESSION_BTRACK + IJEOMA_BTRACK packs via nlm CLI (no second MCP stdio).
#>
param(
  [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
  [int]$SleepMs = 500,
  [string]$LogPath = ""
)
$ErrorActionPreference = "Continue"
if (-not $LogPath) {
  $LogPath = Join-Path $WorkspaceRoot "reports\notebooklm_btrack_lens_pack_push_latest.log"
}
$packRoot = Join-Path $WorkspaceRoot "reports\notebooklm_lens_packs_v1"
$map = @{
  "COMPRESSION_BTRACK" = "aba1f8b1-be62-4367-ac7f-b1a997bb77d4"
  "IJEOMA_BTRACK"      = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
}
if (-not (Get-Command nlm -ErrorAction SilentlyContinue)) {
  throw "nlm not on PATH"
}
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== Push-BtrackNlViaNlm_v1 $ts ===" | Out-File $LogPath -Encoding utf8
$ok = 0; $fail = 0; $skip = 0
foreach ($lens in $map.Keys) {
  $nid = $map[$lens]
  $dir = Join-Path $packRoot $lens
  if (-not (Test-Path $dir)) { continue }
  "[lens $lens] notebook=$nid" | Tee-Object -FilePath $LogPath -Append
  foreach ($fi in (Get-ChildItem $dir -File | Sort-Object Name)) {
    $title = $fi.Name
    if ($title.Length -gt 100) { $title = $title.Substring(0, 100) }
    if ($fi.Length -gt 6MB) {
      "[SKIP large] $($fi.Name)" | Tee-Object -FilePath $LogPath -Append
      $skip++; continue
    }
    try {
      & nlm source add $nid -f $fi.FullName --title $title --wait 2>&1 | Tee-Object -FilePath $LogPath -Append
      if ($LASTEXITCODE -eq 0) { $ok++ } else { $fail++ }
    } catch {
      "[ERR] $($fi.Name) $_" | Tee-Object -FilePath $LogPath -Append
      $fail++
    }
    Start-Sleep -Milliseconds $SleepMs
  }
}
"=== Done ok=$ok fail=$fail skip=$skip ===" | Tee-Object -FilePath $LogPath -Append
py (Join-Path $WorkspaceRoot "scripts\record_comp_nl_auto_upload_v1.py")
if ($fail -gt 0) { exit 1 }
exit 0
