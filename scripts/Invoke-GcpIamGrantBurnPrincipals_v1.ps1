# Grant Vertex AI User for productive burn principals (requires jema12 Owner on project).
param(
    [string]$Project = "gen-lang-client-0846393371",
    [string]$RequiredAccount = "jema12@mkmlife.com",
    [string[]]$Members = @(
        "user:giryun288@gmail.com",
        "user:jema12@mkmlife.com"
    ),
    [string]$Role = "roles/aiplatform.user"
)

$ErrorActionPreference = "Stop"
$active = (gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null | Select-Object -First 1)
if ($active -ne $RequiredAccount) {
    Write-Error "Active gcloud must be $RequiredAccount (now: $active). Run: gcloud auth login $RequiredAccount"
}
gcloud config set project $Project | Out-Host
foreach ($m in $Members) {
    Write-Host "=== IAM bind $m -> $Role ==="
    & gcloud projects add-iam-policy-binding $Project --member=$m --role=$Role --condition=None
    if ($LASTEXITCODE -ne 0) { throw "IAM bind failed for $m" }
}
Write-Host "OK: burn principals granted on $Project"
