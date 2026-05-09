param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TemplateRelative = "scripts\data\trading_guardian_policy_template_v1.json",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$src = Join-Path $WorkspaceRoot $TemplateRelative
$dest = Join-Path $WorkspaceRoot "reports\trading_guardian_policy_latest.json"

if (-not (Test-Path -LiteralPath $src)) {
  throw "Template not found: $src"
}

$reportsDir = Split-Path -Parent $dest
if (-not (Test-Path -LiteralPath $reportsDir)) {
  New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null
}

if ($Force -or -not (Test-Path -LiteralPath $dest)) {
  Copy-Item -LiteralPath $src -Destination $dest -Force
  Write-Host "[ok] Wrote policy: $dest" -ForegroundColor Green
  exit 0
}

Write-Host "[skip] Policy already exists: $dest (use -Force to overwrite)" -ForegroundColor DarkYellow
exit 0
