<#
.SYNOPSIS
  Phase 2: build publish handoff JSON + commander checklist MD (no Buffer API, no auto-post).

.DESCRIPTION
  Run after weekly bundle or before manual LinkedIn post.
  Optional: --ApproveItemId after commander review (calls set_marketing_queue_publish_status_v1.py).
#>
param(
    [string]$WorkspaceRoot = "",
    [string]$ApproveItemId = "",
    [string]$MarkPublishedItemId = ""
)

$ErrorActionPreference = "Stop"
$root = if ($WorkspaceRoot) { (Resolve-Path -LiteralPath $WorkspaceRoot).Path } else { Split-Path -Parent $PSScriptRoot }

$dotenv = Join-Path $root "scripts\Import-WorkspaceDotEnv_v1.ps1"
if (Test-Path -LiteralPath $dotenv) { . $dotenv -WorkspaceRoot $root }

$pull = Join-Path $root "scripts\sync_marketing_queue_to_linkedin_v1.py"
$handoff = Join-Path $root "scripts\build_marketing_publish_handoff_v1.py"
$status = Join-Path $root "scripts\set_marketing_queue_publish_status_v1.py"

Write-Host "== Pull drafted status from LinkedIn queue ==" -ForegroundColor Cyan
& py $pull --pull-linkedin-status
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($ApproveItemId) {
    Write-Host "== Approve item: $ApproveItemId ==" -ForegroundColor Cyan
    & py $status --item-id $ApproveItemId --approve
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($MarkPublishedItemId) {
    Write-Host "== Mark published: $MarkPublishedItemId ==" -ForegroundColor Cyan
    & py $status --item-id $MarkPublishedItemId --mark-published
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "== Build publish handoff ==" -ForegroundColor Cyan
& py $handoff
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] JSON: reports/marketing/marketing_publish_handoff_latest.json" -ForegroundColor Green
Write-Host "[DONE] MD:  reports/marketing/marketing_publish_checklist_latest.md" -ForegroundColor Green
exit 0
