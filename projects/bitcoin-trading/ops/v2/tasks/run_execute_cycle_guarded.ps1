$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\v2\graph\runner.py"
$statePath = Join-Path $projectRoot "memory\v2\latest_state.json"
$riskPolicyPath = Join-Path $projectRoot "ops\v2\policies\risk_policy.yaml"
$approvalPath = Join-Path $projectRoot "memory\v2\ops\execute_approval.json"
$approvalUsedPath = Join-Path $projectRoot "memory\v2\ops\execute_approval_used_jti.jsonl"
$logDir = Join-Path $projectRoot "memory\v2\ops"
$guardLog = Join-Path $logDir "execute_guard.log"
$hmacKey = $env:EXECUTE_APPROVAL_HMAC_KEY

if (-not (Test-Path $runner)) {
    throw "runner.py not found: $runner"
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Set-Location $projectRoot

# 1) Refresh latest posture from read-only cycle
python "$runner" --mode read-only | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "preflight read-only cycle failed with exit code: $LASTEXITCODE"
}

if (-not (Test-Path $statePath)) {
    throw "latest_state.json not found: $statePath"
}

$state = Get-Content -Raw -Path $statePath | ConvertFrom-Json
$rg = $state.risk_mode_guardrail
$blockExecute = $false
$proposedMode = "read-only"
$riskScore = 0

if ($null -ne $rg) {
    if ($null -ne $rg.block_execute) { $blockExecute = [bool]$rg.block_execute }
    if ($null -ne $rg.proposed_mode) { $proposedMode = [string]$rg.proposed_mode }
    if ($null -ne $rg.risk_score) { $riskScore = [int]$rg.risk_score }
}

$ts = (Get-Date).ToString("s")

# 1.5) Respect policy gate: do not run execute when manual approval is required
$requireHumanApproval = $false
if (Test-Path $riskPolicyPath) {
    try {
        $policyCheck = python -c "import yaml, pathlib; p=pathlib.Path(r'$riskPolicyPath'); d=yaml.safe_load(p.read_text(encoding='utf-8')) or {}; rp=(d.get('risk_policy') or {}); print(str(bool(rp.get('require_human_approval_for_execute', False))).lower())"
        if ($LASTEXITCODE -ne 0) { throw 'policy parse failed' }
        $requireHumanApproval = ($policyCheck.Trim() -eq "true")
    } catch {
        # If policy parse fails, fail safe and skip execute.
        $requireHumanApproval = $true
    }
}
if ($requireHumanApproval) {
    if ([string]::IsNullOrWhiteSpace($hmacKey)) {
        Add-Content -Path $guardLog -Value "[$ts] EXECUTE_SKIPPED reason=approval_hmac_key_missing"
        Write-Host "Execute skipped by policy gate: EXECUTE_APPROVAL_HMAC_KEY missing"
        exit 0
    }
    if (-not (Test-Path $approvalPath)) {
        Add-Content -Path $guardLog -Value "[$ts] EXECUTE_SKIPPED reason=require_human_approval_missing"
        Write-Host "Execute skipped by policy gate: approval file missing"
        exit 0
    }
    try {
        $approval = Get-Content -Raw -Path $approvalPath | ConvertFrom-Json
        if ([string]::IsNullOrWhiteSpace($approval.jti)) {
            Add-Content -Path $guardLog -Value "[$ts] EXECUTE_SKIPPED reason=approval_jti_missing"
            Write-Host "Execute skipped by policy gate: approval jti missing"
            exit 0
        }
        $singleUse = $true
        if ($null -ne $approval.single_use) {
            $singleUse = [bool]$approval.single_use
        }
        if ($singleUse -and (Test-Path $approvalUsedPath)) {
            $used = Select-String -Path $approvalUsedPath -Pattern $approval.jti -SimpleMatch -Quiet
            if ($used) {
                Add-Content -Path $guardLog -Value "[$ts] EXECUTE_SKIPPED reason=approval_replay_detected jti=$($approval.jti)"
                Write-Host "Execute skipped by policy gate: approval replay detected (jti=$($approval.jti))"
                exit 0
            }
        }
        $approvedUntil = Get-Date $approval.approved_until_utc
        if ((Get-Date).ToUniversalTime() -gt $approvedUntil.ToUniversalTime()) {
            Add-Content -Path $guardLog -Value "[$ts] EXECUTE_SKIPPED reason=approval_expired approved_until=$($approval.approved_until_utc)"
            Write-Host "Execute skipped by policy gate: approval expired at $($approval.approved_until_utc)"
            exit 0
        }
        $toSign = "$($approval.approved)|$($approval.approved_at_utc)|$($approval.approved_until_utc)|$($approval.approved_by)|$($approval.reason)|$($approval.ttl_minutes)|$($approval.single_use)|$($approval.jti)"
        $sigCheck = python -c "import hmac, hashlib, os, sys; key=os.environ.get('EXECUTE_APPROVAL_HMAC_KEY','').encode('utf-8'); msg=sys.argv[1].encode('utf-8'); sig=(sys.argv[2] or '').strip().lower(); calc=hmac.new(key, msg, hashlib.sha256).hexdigest().lower(); print('ok' if hmac.compare_digest(calc, sig) else 'bad')" "$toSign" "$($approval.signature)"
        if ($LASTEXITCODE -ne 0 -or $sigCheck.Trim() -ne "ok") {
            Add-Content -Path $guardLog -Value "[$ts] EXECUTE_SKIPPED reason=approval_signature_invalid"
            Write-Host "Execute skipped by policy gate: approval signature invalid"
            exit 0
        }
    } catch {
        Add-Content -Path $guardLog -Value "[$ts] EXECUTE_SKIPPED reason=approval_parse_error"
        Write-Host "Execute skipped by policy gate: approval parse error"
        exit 0
    }
}

# 2) Guardrail branch: skip execute when blocked or shadow-proposed
if ($blockExecute -or $proposedMode -eq "shadow") {
    $reason = if ($blockExecute) { "block_execute=true" } else { "proposed_mode=shadow" }
    Add-Content -Path $guardLog -Value "[$ts] EXECUTE_SKIPPED reason=$reason risk_score=$riskScore"
    Write-Host "Execute skipped by guardrail: $reason (risk_score=$riskScore)"
    exit 0
}

# 3) Execute only when guardrail allows
if ($requireHumanApproval) {
    python "$runner" --mode execute --execute-approved
} else {
    python "$runner" --mode execute
}
if ($LASTEXITCODE -ne 0) {
    throw "v2 guarded execute cycle failed with exit code: $LASTEXITCODE"
}

Add-Content -Path $guardLog -Value "[$ts] EXECUTE_RAN risk_score=$riskScore"
Write-Host "Execute ran (risk_score=$riskScore)"
if ($requireHumanApproval) {
    $usedEvent = [ordered]@{
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        jti = $approval.jti
        single_use = [bool]$approval.single_use
        approved_by = $approval.approved_by
        approved_until_utc = $approval.approved_until_utc
        result = "consumed"
    } | ConvertTo-Json -Compress
    Add-Content -Path $approvalUsedPath -Value $usedEvent
    if ([bool]$approval.single_use) {
        Remove-Item $approvalPath -Force -ErrorAction SilentlyContinue
        Add-Content -Path $guardLog -Value "[$ts] APPROVAL_CONSUMED jti=$($approval.jti)"
    } else {
        Add-Content -Path $guardLog -Value "[$ts] APPROVAL_REUSED_ALLOWED jti=$($approval.jti)"
    }
}
