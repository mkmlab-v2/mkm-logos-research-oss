param(
  [string]$WorkflowFile = "gpu-engine-benchmark-bundle.yml",
  [string]$Branch = "main",
  [ValidateSet("schedule", "workflow_dispatch")]
  [string]$Event = "schedule",
  [switch]$ShowFailedLogSnippet
)

$ErrorActionPreference = "Stop"

Write-Host "Checking latest scheduled run"
Write-Host "  workflow=$WorkflowFile branch=$Branch event=$Event"

$runsJson = gh run list --workflow $WorkflowFile --branch $Branch --event $Event --limit 1 --json databaseId,displayTitle,headBranch,status,conclusion,url,createdAt
$runs = $runsJson | ConvertFrom-Json

if (-not $runs -or $runs.Count -eq 0) {
  Write-Host "No runs found for event=$Event."
  exit 2
}

$run = $runs[0]
$runId = [string]$run.databaseId

Write-Host "Latest run:"
Write-Host "  id=$runId status=$($run.status) conclusion=$($run.conclusion)"
Write-Host "  createdAt=$($run.createdAt)"
Write-Host "  url=$($run.url)"

$jobsJson = gh run view $runId --json jobs
$jobsDoc = $jobsJson | ConvertFrom-Json
$jobs = @($jobsDoc.jobs)

if ($jobs.Count -eq 0) {
  Write-Host "No jobs found in run."
  exit 2
}

$failedJobs = @()
foreach ($job in $jobs) {
  $name = [string]$job.name
  $status = [string]$job.status
  $conclusion = [string]$job.conclusion
  Write-Host "  - $name :: status=$status conclusion=$conclusion"
  if ($conclusion -ne "success") {
    $failedJobs += $job
  }
}

if ($failedJobs.Count -eq 0) {
  Write-Host "RESULT: PASS (latest run is healthy)"
  exit 0
}

Write-Host "RESULT: FAIL (latest run has failed jobs)"

if ($ShowFailedLogSnippet.IsPresent) {
  foreach ($job in $failedJobs) {
    $jobId = [string]$job.databaseId
    Write-Host ""
    Write-Host "---- Failed job log tail: $($job.name) (id=$jobId) ----"
    gh run view $runId --job $jobId --log | Select-Object -Last 80
  }
}

exit 1
