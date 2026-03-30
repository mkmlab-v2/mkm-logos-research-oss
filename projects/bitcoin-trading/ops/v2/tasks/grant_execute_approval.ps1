param(
    [int]$Minutes = 30,
    [string]$Reason = "manual approval",
    [string]$Approver = $env:USERNAME,
    [ValidateSet("true", "false")]
    [string]$SingleUse = "true"
)

$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$approvalDir = Join-Path $projectRoot "memory\v2\ops"
$approvalPath = Join-Path $approvalDir "execute_approval.json"
$hmacKey = $env:EXECUTE_APPROVAL_HMAC_KEY

if ([string]::IsNullOrWhiteSpace($hmacKey)) {
    throw "Missing EXECUTE_APPROVAL_HMAC_KEY environment variable"
}

New-Item -ItemType Directory -Path $approvalDir -Force | Out-Null

$now = Get-Date
$until = $now.ToUniversalTime().AddMinutes($Minutes)
$singleUseBool = ($SingleUse.ToLowerInvariant() -eq "true")
$jti = python -c "import uuid; print(uuid.uuid4().hex)"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($jti)) {
    throw "Failed to generate approval token jti"
}
$jti = $jti.Trim()

$payload = [ordered]@{
    approved = $true
    approved_at_utc = $now.ToUniversalTime().ToString("o")
    approved_until_utc = $until.ToString("o")
    approved_by = $Approver
    reason = $Reason
    ttl_minutes = $Minutes
    single_use = $singleUseBool
    jti = $jti
    sig_alg = "HMAC-SHA256"
    signature = ""
}

$toSign = "$($payload.approved)|$($payload.approved_at_utc)|$($payload.approved_until_utc)|$($payload.approved_by)|$($payload.reason)|$($payload.ttl_minutes)|$($payload.single_use)|$($payload.jti)"
$signature = python -c "import hmac, hashlib, os, sys; key=os.environ.get('EXECUTE_APPROVAL_HMAC_KEY','').encode('utf-8'); msg=sys.argv[1].encode('utf-8'); print(hmac.new(key, msg, hashlib.sha256).hexdigest())" "$toSign"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($signature)) {
    throw "Failed to generate HMAC signature for execute approval token"
}
$payload.signature = $signature.Trim()

$payload | ConvertTo-Json -Depth 5 | Set-Content -Path $approvalPath -Encoding UTF8
Write-Host "Execute approval granted until $($payload.approved_until_utc)"
Write-Host "JTI: $($payload.jti)"
Write-Host "SingleUse: $($payload.single_use)"
Write-Host "File: $approvalPath"
