param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("a_track")]
    [string]$Target,

    [Parameter(Mandatory = $true)]
    [ValidateSet("S2_PAPER_STRICT", "S3_PAPER_SCALED", "S4_LIMITED_LIVE")]
    [string]$RequestedStage,

    [Parameter(Mandatory = $true)]
    [ValidateSet("approve", "reject")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$Approver,

    [string]$Reason = "",

    [switch]$Strict
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-WorkspaceRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function New-UtcIso8601 {
    return [DateTime]::UtcNow.ToString("o")
}

$workspaceRoot = Get-WorkspaceRoot
$reportsDir = Join-Path $workspaceRoot "reports"
$latestPath = Join-Path $reportsDir "a_track_promotion_decision_latest.json"
$auditPath = Join-Path $reportsDir "a_track_promotion_decision_audit_log.jsonl"

if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

$status = if ($Action -eq "approve") { "accepted" } else { "rejected" }

$payload = [ordered]@{
    schema = "a_track_promotion_cli_decision_v1"
    generated_at = New-UtcIso8601
    target = $Target
    requested_stage = $RequestedStage
    action = $Action
    status = $status
    approver = $Approver
    reason = $Reason
    strict_mode = [bool]$Strict
    source = @{
        script = "scripts/approve_intervention_promotion.ps1"
        workspace_root = $workspaceRoot
    }
}

$json = $payload | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText($latestPath, "$json`n", [Text.UTF8Encoding]::new($false))

$jsonl = ($payload | ConvertTo-Json -Depth 6 -Compress)
[IO.File]::AppendAllText($auditPath, "$jsonl`n", [Text.UTF8Encoding]::new($false))

Write-Host "WROTE: $latestPath"
Write-Host "AUDIT_APPEND: $auditPath"
Write-Host "target=$Target requested_stage=$RequestedStage action=$Action status=$status approver=$Approver"
