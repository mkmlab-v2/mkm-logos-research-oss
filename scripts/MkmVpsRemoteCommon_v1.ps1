# Shared VPS scp/ssh helpers (key, timeout, user@host). Dot-source from deploy scripts.
# Usage: . (Join-Path $PSScriptRoot "MkmVpsRemoteCommon_v1.ps1")

function Get-MkmEnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    return ""
}

function Test-MkmHasSshOption([string[]]$LeadingArgs, [string]$OptionName) {
    for ($i = 0; $i -lt $LeadingArgs.Count; $i++) {
        $arg = $LeadingArgs[$i]
        if ($arg -eq "-o" -and ($i + 1) -lt $LeadingArgs.Count) {
            if ($LeadingArgs[$i + 1] -like "$OptionName=*") { return $true }
        }
        if ($arg -like "$OptionName=*") { return $true }
    }
    return $false
}

function Test-MkmHasIdentityArgs([string[]]$LeadingArgs) {
    for ($i = 0; $i -lt $LeadingArgs.Count; $i++) {
        $arg = $LeadingArgs[$i]
        if ($arg -eq "-i" -or $arg -like "-i*") { return $true }
        if ($arg -eq "-o" -and ($i + 1) -lt $LeadingArgs.Count) {
            if ($LeadingArgs[$i + 1] -like "IdentityFile=*") { return $true }
        }
        if ($arg -like "IdentityFile=*") { return $true }
    }
    return $false
}

function Get-MkmVpsSshExtraArgs() {
    $extraArgs = @()
    $extraRaw = Get-MkmEnvAny "MKM_VPS_SCP_EXTRA_ARGS"
    if (-not [string]::IsNullOrWhiteSpace($extraRaw)) {
        $extraArgs = $extraRaw -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    }
    foreach ($pair in @(
            @("ConnectTimeout", "20"),
            @("ServerAliveInterval", "15"),
            @("ServerAliveCountMax", "3"),
            @("BatchMode", "yes")
        )) {
        if (-not (Test-MkmHasSshOption -LeadingArgs $extraArgs -OptionName $pair[0])) {
            $extraArgs += @("-o", "$($pair[0])=$($pair[1])")
        }
    }
    return $extraArgs
}

function Get-MkmVpsRemoteTarget() {
    $hostName = Get-MkmEnvAny "MKM_VPS_HOST"
    if ([string]::IsNullOrWhiteSpace($hostName)) { $hostName = "vps-mkmlife" }
    $user = Get-MkmEnvAny "MKM_VPS_USER"
    if ([string]::IsNullOrWhiteSpace($user)) { $user = "root" }
    return @{
        HostName  = $hostName
        User      = $user
        Remote    = "${user}@${hostName}"
        ExtraArgs = (Get-MkmVpsSshExtraArgs)
    }
}

function Assert-MkmVpsNonInteractive([hashtable]$Target) {
    if (-not (Test-MkmHasIdentityArgs -LeadingArgs $Target.ExtraArgs)) {
        throw "[mkm-vps] blocked: set MKM_VPS_SCP_EXTRA_ARGS with -i <key> (non-interactive; prevents SSH hang)."
    }
}

function Invoke-MkmVpsScp {
    param(
        [Parameter(Mandatory = $true)][string]$LocalPath,
        [Parameter(Mandatory = $true)][string]$RemoteSpec
    )
    $t = Get-MkmVpsRemoteTarget
    Assert-MkmVpsNonInteractive $t
    $argv = @()
    foreach ($a in $t.ExtraArgs) { $argv += $a }
    $argv += $LocalPath
    $argv += $RemoteSpec
    & scp @argv
    if ($LASTEXITCODE -ne 0) { throw "[mkm-vps] scp failed ($LASTEXITCODE): $LocalPath -> $RemoteSpec" }
}

function Invoke-MkmVpsSsh {
    param(
        [Parameter(Mandatory = $true)][string]$RemoteCommand,
        [string]$Remote = ""
    )
    $t = Get-MkmVpsRemoteTarget
    if ([string]::IsNullOrWhiteSpace($Remote)) { $Remote = $t.Remote }
    Assert-MkmVpsNonInteractive $t
    $argv = @()
    foreach ($a in $t.ExtraArgs) { $argv += $a }
    $argv += $Remote
    $argv += $RemoteCommand
    & ssh @argv
    if ($LASTEXITCODE -ne 0) { throw "[mkm-vps] ssh failed ($LASTEXITCODE)" }
}
