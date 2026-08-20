# ==============================================================================
# USPC - Universal Personal Cloud Platform (Kubernetes Teardown Alias)
# ==============================================================================

[CmdletBinding()]
param (
    [string]$Namespace = "uspc",
    [switch]$PurgeData = $false,
    [switch]$Force = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$ScriptDir\k8s-down.ps1" -Namespace $Namespace -PurgeData:$PurgeData -Force:$Force
