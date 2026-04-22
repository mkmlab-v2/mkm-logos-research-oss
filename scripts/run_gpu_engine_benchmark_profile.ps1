param(
  [ValidateSet("quick", "standard", "high")]
  [string]$Profile = "standard",
  [string]$Ref = "main",
  [string]$MaxRegressionPct = "10",
  [switch]$UploadArtifacts,
  [switch]$Watch
)

$ErrorActionPreference = "Stop"

$sampleCount = switch ($Profile) {
  "quick" { "3" }
  "standard" { "5" }
  "high" { "7" }
  default { throw "Unsupported profile: $Profile" }
}

$uploadArtifactsValue = if ($UploadArtifacts.IsPresent) { "true" } else { "false" }

$args = @(
  "workflow", "run", "gpu-engine-benchmark-bundle.yml",
  "--ref", $Ref,
  "-f", "run_self_hosted_gpu=true",
  "-f", "require_cuda_on_gpu_runner=true",
  "-f", "max_regression_pct=$MaxRegressionPct",
  "-f", "sample_count=$sampleCount",
  "-f", "upload_artifacts=$uploadArtifactsValue"
)

Write-Host "Dispatching GPU benchmark workflow"
Write-Host "  profile=$Profile sample_count=$sampleCount ref=$Ref upload_artifacts=$uploadArtifactsValue"

$dispatchOutput = & gh @args
$dispatchOutput | Write-Host

if (-not $Watch.IsPresent) {
  return
}

$runUrl = ($dispatchOutput | Select-String -Pattern "https://github.com/.*/actions/runs/\d+").Matches.Value
if ([string]::IsNullOrWhiteSpace($runUrl)) {
  throw "Failed to parse workflow run URL from gh output."
}

$runId = ($runUrl -split "/")[-1]
Write-Host "Watching run id: $runId"
& gh run watch $runId --interval 20 --exit-status
