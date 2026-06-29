# Non-interactive gcloud cloud-shell ssh/scp (avoids PuTTY "Store key in cache?" hang).
param(
    [Parameter(Mandatory = $true)]
    [string]$Command,
    [string]$Project = "gen-lang-client-0846393371",
    [string]$HostKey = "ecdsa-sha2-nistp256 256 SHA256:5/CRJcYwiwMfrafnBjNHe6RWC7qrWlUAKmrtab0v2wQ"
)

$sshFlags = @(
    "--project", $Project,
    "--authorize-session",
    "--ssh-flag=-batch",
    "--ssh-flag=-hostkey",
    "--ssh-flag=$HostKey",
    "--command=$Command"
)
& gcloud cloud-shell ssh @sshFlags
