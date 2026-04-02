# Copies showroom static assets into a local or UNC web root (e.g. before rsync/scp to jemaai.cloud).
# Does not configure nginx on the server — deploy paths only.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File deploy_showroom_static.ps1
#   powershell ... -WebRoot "D:\staging\jemaai"
# Env: JEMAAI_WEB_ROOT — used if -WebRoot omitted
#
# Copies:
#   public_showroom_poll.html
#   showroom_public_bundle_v1.json  (from jemaai-cloud-mvp; run build_showroom_display_bundle.ps1 first)

param(
    [string]$WebRoot = "",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$mvp = Join-Path $here "jemaai-cloud-mvp"
$files = @(
    @{ Name = "public_showroom_poll.html"; Src = Join-Path $mvp "public_showroom_poll.html" },
    @{ Name = "showroom_public_bundle_v1.json"; Src = Join-Path $mvp "showroom_public_bundle_v1.json" }
)

$destRoot = $WebRoot
if ([string]::IsNullOrWhiteSpace($destRoot)) {
    $destRoot = [Environment]::GetEnvironmentVariable("JEMAAI_WEB_ROOT", "Process")
}

if ([string]::IsNullOrWhiteSpace($destRoot)) {
    Write-Host "[deploy-showroom] SKIP: set -WebRoot or JEMAAI_WEB_ROOT to a directory (e.g. \\server\share\jemaai or D:\www\jemaai)."
    exit 0
}

if (-not (Test-Path -LiteralPath $destRoot)) {
    throw "[deploy-showroom] destination does not exist: $destRoot"
}

foreach ($f in $files) {
    if (-not (Test-Path -LiteralPath $f.Src)) {
        Write-Warning "[deploy-showroom] missing source: $($f.Src) — run build_showroom_display_bundle.ps1"
        continue
    }
    $out = Join-Path $destRoot $f.Name
    if ($WhatIf) {
        Write-Host "[deploy-showroom] WHATIF: copy $($f.Src) -> $out"
    } else {
        Copy-Item -LiteralPath $f.Src -Destination $out -Force
        Write-Host "[deploy-showroom] OK: $out"
    }
}

Write-Host "[deploy-showroom] Done. On Linux nginx host: copy to /var/www/jemaai/ and `nginx -t && systemctl reload nginx` (see nginx_snippets/jemaai_showroom_ui.conf)."
