# Local-main / SSH-ops command profile
# Usage:
#   . C:\workspace\projects\bitcoin-trading\ops\v2\tasks\set-local-main-aliases.ps1

Set-StrictMode -Version Latest

function devsync {
    [CmdletBinding()]
    param(
        [string]$Branch = "main"
    )

    git fetch --all --prune
    git pull --rebase origin $Branch
    git status -sb
}

function gsync {
    [CmdletBinding()]
    param()

    & "C:\workspace\scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1"
}

function gsyncall {
    [CmdletBinding()]
    param(
        [string]$Branch = "main"
    )

    devsync -Branch $Branch
    gsync
}

function server-check {
    [CmdletBinding()]
    param(
        [string]$Host = $env:MKM_VPS_HOST,
        [string]$User = $env:MKM_VPS_USER
    )

    if (-not $Host -or -not $User) {
        throw "Set MKM_VPS_HOST and MKM_VPS_USER environment variables first."
    }

    ssh "$User@$Host" "hostname; uptime; docker ps --format 'table {{.Names}}\t{{.Status}}' || true"
}

function deploy {
    [CmdletBinding()]
    param(
        [string]$Host = $env:MKM_VPS_HOST,
        [string]$User = $env:MKM_VPS_USER,
        [string]$RemotePath = "/opt/bitcoin-trading"
    )

    if (-not $Host -or -not $User) {
        throw "Set MKM_VPS_HOST and MKM_VPS_USER environment variables first."
    }

    ssh "$User@$Host" "cd $RemotePath && git pull origin main || git pull gitea main || true"
}

Write-Host "Commands loaded: devsync, gsync, gsyncall, server-check, deploy"
