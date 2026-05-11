param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$ProposalJson = "reports/trading_execution_proposal_latest.json",
  [ValidateSet("GO", "NO_GO")]
  [string]$Decision = "GO",
  [string]$Approver = "commander",
  [string]$ApprovalNote = "",
  [int]$ValidHours = 24
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location $WorkspaceRoot

if (-not [System.IO.Path]::IsPathRooted($ProposalJson)) {
  $ProposalJson = Join-Path $WorkspaceRoot $ProposalJson
}
$ProposalJson = (Resolve-Path -LiteralPath $ProposalJson).Path
if (-not (Test-Path -LiteralPath $ProposalJson)) {
  throw "Proposal file not found: $ProposalJson"
}

$proposalRaw = Get-Content -LiteralPath $ProposalJson -Encoding UTF8 -Raw
# Windows PowerShell 5.1: ConvertFrom-Json has no -Depth; deep nesting is uncommon for proposal v1.
$proposal = $proposalRaw | ConvertFrom-Json
if ($proposal.schema -ne "trading_execution_proposal_v1") {
  throw "Proposal schema mismatch: expected trading_execution_proposal_v1, got '$($proposal.schema)'."
}
if (-not $proposal.proposal_id) {
  throw "Proposal missing proposal_id."
}

$sha = (Get-FileHash -LiteralPath $ProposalJson -Algorithm SHA256).Hash.ToLowerInvariant()
$now = [DateTimeOffset]::UtcNow
$validUntil = if ($Decision -eq "GO") { $now.AddHours([double]$ValidHours) } else { $now.AddHours(1) }

$wr = ([string]$WorkspaceRoot).TrimEnd('\')
$pr = [string]$ProposalJson
if (-not $pr.StartsWith($wr, [StringComparison]::OrdinalIgnoreCase)) {
  throw "Proposal path must be under WorkspaceRoot. root=$wr proposal=$pr"
}
$artifactRel = $pr.Substring($wr.Length).TrimStart('\').Replace('\', '/')

$approval = [ordered]@{
  schema = "trading_human_execution_approval_v1"
  domain = "trading"
  track = "A"
  proposal_id = [string]$proposal.proposal_id
  proposal_ref = @{
    artifact_path = $artifactRel
    source_rail = "A"
  }
  proposal_body_sha256 = $sha
  decision = $Decision
  approved_at_utc = $now.ToString("o")
  valid_until_utc = $validUntil.ToString("o")
  approver_label = $Approver
  approval_note = $(if ([string]::IsNullOrWhiteSpace($ApprovalNote)) { "Operator decision from approve_trading_execution_v1.ps1." } else { $ApprovalNote })
  nonce = ("trade-approval-" + $now.ToString("yyyyMMddTHHmmssZ"))
}

$out = Join-Path $WorkspaceRoot "reports/trading_human_execution_approval_latest.json"
$audit = Join-Path $WorkspaceRoot "reports/trading_human_execution_approval_audit_log.jsonl"
$approvalJson = $approval | ConvertTo-Json -Depth 10
[IO.File]::WriteAllText($out, "$approvalJson`n", [Text.UTF8Encoding]::new($false))
[IO.File]::AppendAllText($audit, (($approval | ConvertTo-Json -Depth 10 -Compress) + "`n"), [Text.UTF8Encoding]::new($false))

Write-Host "WROTE: $out"
Write-Host "AUDIT_APPEND: $audit"
Write-Host ("proposal_id={0} decision={1} sha256={2}" -f $approval.proposal_id, $Decision, $sha)

