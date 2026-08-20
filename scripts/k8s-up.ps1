# ==============================================================================
# USPC - Universal Personal Cloud Platform (Kubernetes / K3s Up Alias)
# ==============================================================================

[CmdletBinding()]
param (
    [string]$StorageDrive = "D:\MyCloud",
    [string]$Namespace = "uspc",
    [switch]$PortForward = $true,
    [switch]$SkipWait = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$ScriptDir\setup-windows-k8s.ps1" -StorageDrive $StorageDrive -Namespace $Namespace -PortForward:$PortForward -SkipWait:$SkipWait
