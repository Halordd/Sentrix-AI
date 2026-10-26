#Requires -Version 5.1
<#
.SYNOPSIS
    Synchronize the SENTRIX source tree to the five local VMs.

.DESCRIPTION
    Copies the subset of source each VM needs into ~/sentrix-src. Runtime paths
    are intentionally separate; see DEPLOYMENT.md. Use -DryRun to print the
    commands without executing them.

.PARAMETER Only
    Optional VM names to sync: VM01, VM02, VM03, VM04, VM05.

.PARAMETER DryRun
    Print commands without copying.

.EXAMPLE
    .\sync-source.ps1
    .\sync-source.ps1 -Only VM01,VM04
    .\sync-source.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$SshDir = "",
    [string[]]$Only = @(),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) { $RepoRoot = $PSScriptRoot }
if (-not $SshDir) {
    $profileDir = $env:USERPROFILE
    if (-not $profileDir) { $profileDir = $HOME }
    $SshDir = Join-Path $profileDir ".ssh"
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$SshDir = (Resolve-Path -LiteralPath $SshDir).Path

$targets = @(
    [pscustomobject]@{
        Name = "VM01"; IP = "10.20.10.10"; Key = "sentrix_m1_vm01_ed25519"
        Remote = "sentrix-src"
        Paths = @("frontend", "backend", "database", "docs", "lab", "README.md", "FLOWCHART.md", "DEPLOYMENT.md")
    },
    [pscustomobject]@{
        Name = "VM02"; IP = "10.20.10.20"; Key = "sentrix_m1_vm02_ed25519"
        Remote = "sentrix-src"
        Paths = @("database", "docs", "README.md", "FLOWCHART.md", "DEPLOYMENT.md")
    },
    [pscustomobject]@{
        Name = "VM03"; IP = "10.20.10.30"; Key = "sentrix_m1_vm03_ed25519"
        Remote = "sentrix-src"
        Paths = @("backend/ai_service", "backend/deploy/sentrix-ai-mock.service", "README.md", "FLOWCHART.md", "DEPLOYMENT.md")
    },
    [pscustomobject]@{
        Name = "VM04"; IP = "10.20.10.40"; Key = "sentrix_m1_vm04_ed25519"
        Remote = "sentrix-src"
        Paths = @("backend/worker", "backend/deploy", "README.md", "FLOWCHART.md", "DEPLOYMENT.md")
    },
    [pscustomobject]@{
        Name = "VM05"; IP = "10.20.20.20"; Key = "sentrix_m1_vm05_ed25519"
        Remote = "sentrix-src"
        Paths = @("lab", "README.md", "FLOWCHART.md", "DEPLOYMENT.md")
    }
)

if ($Only.Count -gt 0) {
    $wanted = @($Only | ForEach-Object { $_.ToUpperInvariant() })
    $targets = @($targets | Where-Object { $wanted -contains $_.Name })
    if ($targets.Count -eq 0) {
        throw "No matching VMs. Use VM01..VM05."
    }
}

function Invoke-External {
    param([string]$Exe, [string[]]$Arguments)
    if ($DryRun) {
        Write-Host ("DRY-RUN: {0} {1}" -f $Exe, ($Arguments -join " "))
        return
    }
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Exe failed with exit code $LASTEXITCODE"
    }
}

foreach ($target in $targets) {
    $keyPath = Join-Path $SshDir $target.Key
    if (-not (Test-Path -LiteralPath $keyPath)) {
        throw "Missing SSH key: $keyPath"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "DEPLOYMENT.md"))) {
        throw "Run this script from the repository root (DEPLOYMENT.md not found)."
    }

    Write-Host ""
    Write-Host "=== $($target.Name) $($target.IP) ===" -ForegroundColor Cyan

    $sshBase = @(
        "-i", $keyPath,
        "-o", "BatchMode=yes",
        "-o", "IdentitiesOnly=yes",
        "-o", "ConnectTimeout=10"
    )

    foreach ($relative in $target.Paths) {
        $source = Join-Path $RepoRoot $relative
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Missing source path: $source"
        }
        $remoteDir = "~/sentrix-src"
        if ($relative -eq "backend") { $remoteDir = "~/sentrix-src" }
        elseif ($relative -eq "backend/deploy") { $remoteDir = "~/sentrix-src/backend" }
        elseif ($relative.StartsWith("backend/deploy/")) { $remoteDir = "~/sentrix-src/deploy" }
        elseif ($relative.StartsWith("backend/")) { $remoteDir = "~/sentrix-src/backend" }

        Invoke-External "ssh" ($sshBase + @("sentrixadmin@$($target.IP)", "mkdir -p $remoteDir"))
        Invoke-External "scp" (@("-i", $keyPath, "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-q", "-r", $source, "sentrixadmin@$($target.IP):$remoteDir/"))
    }
}

Write-Host ""
Write-Host "Source sync complete." -ForegroundColor Green
Write-Host "Frontend runtime copy is separate: sudo cp ~/sentrix-web/{app,api,repository,apiRepository}.js /var/www/sentrix/"
