param(
    [switch]$ApplyUserScope
)

$ErrorActionPreference = "Stop"

Write-Host "[graph-env] Template mode"
Write-Host "[graph-env] Fill values in this script before applying."

# Fill these values before running with -ApplyUserScope.
$GRAPH_TENANT_ID = "REPLACE_WITH_TENANT_ID"
$GRAPH_CLIENT_ID = "REPLACE_WITH_CLIENT_ID"
$GRAPH_CLIENT_SECRET = "REPLACE_WITH_CLIENT_SECRET"
$GRAPH_SENDER_UPN = "REPLACE_WITH_SENDER_UPN"
$GRAPH_RECIPIENT_EMAIL = "admin@no1kmedi.com"
$GRAPH_MAIL_SUBJECT = "[Action Required] Macro Risk Warning API 파일럿 Base URL 확정 요청"
$GRAPH_MAIL_BODY_FILE = "docs/final/artifacts/macro_risk_warning_api_base_url_confirmation_email_live_v1.md"

$pairs = @{
    GRAPH_TENANT_ID = $GRAPH_TENANT_ID
    GRAPH_CLIENT_ID = $GRAPH_CLIENT_ID
    GRAPH_CLIENT_SECRET = $GRAPH_CLIENT_SECRET
    GRAPH_SENDER_UPN = $GRAPH_SENDER_UPN
    GRAPH_RECIPIENT_EMAIL = $GRAPH_RECIPIENT_EMAIL
    GRAPH_MAIL_SUBJECT = $GRAPH_MAIL_SUBJECT
    GRAPH_MAIL_BODY_FILE = $GRAPH_MAIL_BODY_FILE
}

$missing = @()
foreach ($k in @("GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET", "GRAPH_SENDER_UPN")) {
    if ($pairs[$k] -like "REPLACE_WITH_*") {
        $missing += $k
    }
}

if ($missing.Count -gt 0) {
    Write-Host "[graph-env] Missing required filled values:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host " - $_" -ForegroundColor Yellow }
    Write-Host "[graph-env] Edit this file and replace placeholders first."
    exit 1
}

if (-not $ApplyUserScope) {
    Write-Host "[graph-env] Dry-run preview (nothing written):"
    foreach ($entry in $pairs.GetEnumerator()) {
        if ($entry.Key -eq "GRAPH_CLIENT_SECRET") {
            Write-Host ("  {0}={1}" -f $entry.Key, "***masked***")
        } else {
            Write-Host ("  {0}={1}" -f $entry.Key, $entry.Value)
        }
    }
    Write-Host "[graph-env] Re-run with -ApplyUserScope to persist as user environment variables."
    exit 0
}

foreach ($entry in $pairs.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable($entry.Key, [string]$entry.Value, "User")
}

Write-Host "[graph-env] User-scope environment variables updated."
Write-Host "[graph-env] Open a new terminal and run:"
Write-Host "  py scripts/send_macro_risk_baseurl_confirmation_via_graph.py"
