param(
  [Parameter(Mandatory = $false)]
  [double]$LatencyImprovement = 0,

  [Parameter(Mandatory = $false)]
  [double]$ErrorRateReduction = 0,

  [Parameter(Mandatory = $false)]
  [int]$Retries = 0,

  [Parameter(Mandatory = $false)]
  [string]$Action = "",

  [Parameter(Mandatory = $false)]
  [string]$Role = "",

  [Parameter(Mandatory = $false)]
  [string]$BranchName = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($BranchName)) {
  $BranchName = (git rev-parse --abbrev-ref HEAD).Trim()
}

$issues = @()

function Add-Issue {
  param(
    [Parameter(Mandatory = $true)][string]$Code,
    [Parameter(Mandatory = $true)][string]$Message
  )
  $script:issues += [pscustomobject]@{
    issue_code = $Code
    message = $Message
  }
}

# Loop breaker: max_retries=3, at 3 must switch strategy.
if ($Retries -ge 3 -and $Action -ne "change_strategy") {
  Add-Issue -Code "RETRY_STRATEGY_REQUIRED" -Message "Retry gate failed: retries=$Retries requires action=change_strategy."
}

# Promotion hard gate: AND condition.
if ($LatencyImprovement -lt 15) {
  Add-Issue -Code "PROMOTION_LATENCY_GATE_FAILED" -Message "Promotion gate failed: latency_improvement($LatencyImprovement) < 15."
}
if ($ErrorRateReduction -lt 20) {
  Add-Issue -Code "PROMOTION_ERROR_RATE_GATE_FAILED" -Message "Promotion gate failed: error_rate_reduction($ErrorRateReduction) < 20."
}

# Mutator isolation: commits only on b-track-* branch naming.
if ($Role -eq "Mutator" -and $BranchName -notlike "b-track-*") {
  Add-Issue -Code "MUTATOR_BRANCH_ISOLATION" -Message "Branch isolation failed: Mutator role requires branch name b-track-*, current=$BranchName."
}

$summary = [ordered]@{
  timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
  branch_name = $BranchName
  role = $Role
  retries = $Retries
  action = $Action
  latency_improvement = $LatencyImprovement
  error_rate_reduction = $ErrorRateReduction
  passed = ($issues.Count -eq 0)
  issues = @($issues)
}

$json = $summary | ConvertTo-Json -Depth 4
Write-Output $json

if ($issues.Count -gt 0) {
  exit 1
}

exit 0
