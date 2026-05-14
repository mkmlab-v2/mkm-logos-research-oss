#Requires -Version 5.1
<#
.SYNOPSIS
  Idempotent IAM bootstrap for MKM lab: Vertex AI + Discovery Engine (Agent Search) grounding path.

.DESCRIPTION
  - Enables aiplatform.googleapis.com (Vertex / Agent Platform).
  - Grants roles/discoveryengine.viewer and roles/aiplatform.user to:
      - Default Compute Engine service account
      - Vertex AI Platform service agent (service-PROJECT@gcp-sa-aiplatform.iam.gserviceaccount.com)
      - Optional: current gcloud user (if not already Owner/Editor on project)

  Re-run safely; duplicate bindings merge.

.PARAMETER ProjectId
  GCP project id (default: mkm-lab-agi-2025)

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Bootstrap-MkmVertexSearchGroundingIam_v1.ps1
#>
param(
    [string] $ProjectId = "mkm-lab-agi-2025"
)

$ErrorActionPreference = "Stop"

function Invoke-Gcloud {
    param([string[]] $GcloudArgs)
    & gcloud @GcloudArgs
    if ($LASTEXITCODE -ne 0) { throw "gcloud failed: gcloud $($GcloudArgs -join ' ')" }
}

$num = (Invoke-Gcloud @("projects", "describe", $ProjectId, "--format=value(projectNumber)")).Trim()
if (-not $num) { throw "Could not resolve project number for $ProjectId" }

$computeSa = "${num}-compute@developer.gserviceaccount.com"
$aiplatformSa = "service-${num}@gcp-sa-aiplatform.iam.gserviceaccount.com"

Write-Host "Project=$ProjectId number=$num"
Invoke-Gcloud @("services", "enable", "aiplatform.googleapis.com", "--project=$ProjectId")

$rows = @(
    @{ Member = "serviceAccount:$computeSa"; Role = "roles/discoveryengine.viewer" }
    @{ Member = "serviceAccount:$computeSa"; Role = "roles/aiplatform.user" }
    @{ Member = "serviceAccount:$aiplatformSa"; Role = "roles/discoveryengine.viewer" }
)
foreach ($row in $rows) {
    $member = $row.Member
    $role = $row.Role
    Write-Host "IAM: $member -> $role"
    Invoke-Gcloud @(
        "projects", "add-iam-policy-binding", $ProjectId,
        "--member=$member", "--role=$role", "--quiet"
    )
}

$acct = (Invoke-Gcloud @("config", "get-value", "account")).Trim()
if ($acct -and $acct -like "*@*") {
    Write-Host "IAM: user:$acct -> roles/discoveryengine.viewer (skip if already owner)"
    try {
        Invoke-Gcloud @(
            "projects", "add-iam-policy-binding", $ProjectId,
            "--member=user:$acct", "--role=roles/discoveryengine.viewer", "--quiet"
        )
    } catch { Write-Warning $_ }
    try {
        Invoke-Gcloud @(
            "projects", "add-iam-policy-binding", $ProjectId,
            "--member=user:$acct", "--role=roles/aiplatform.user", "--quiet"
        )
    } catch { Write-Warning $_ }
}

Write-Host "Done. Run: py scripts/run_vertex_gemini_vertex_ai_search_grounding_smoke_v1.py --project $ProjectId"
